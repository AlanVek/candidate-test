import re

regex = re.compile(r'  reg \[(.*)\] (\S*) \[(.*)\];\n  initial begin\n((    \S*\[\S*\] = \S*;\n)*)  end\n')

def get_mem_name(definition : str) -> str:
    start_name = definition.find(']')
    end_name = definition.rfind('[')

    if start_name != -1 and end_name != -1:
        return definition[start_name + 1 : end_name].strip()

    else: return ''

def get_number(value_line : str) -> '':
    init_pos = value_line.find("'")

    if init_pos != -1:
        return value_line[init_pos + 2 : -1]

    else: return ''

def get_padding(line : str) -> int:
    i = 0
    while i < len(line) and line[i] == ' ': i += 1
    return i

def parser(filename):
    with open(filename, 'r+') as file:

        content = file.read()
        dump_name = 'memdump{}.mem'
        open_name = '$readmemh("memdump{}.mem", {});'

        for i, match in enumerate(re.finditer(regex, content)):
            idx_start, idx_end = match.start(), match.end()

            newfilename = dump_name.format(i)
            res_numbers = ''

            lines = content[idx_start : idx_end].splitlines()

            for j, line in enumerate(lines):
                if not j:
                    name, keep_line = get_mem_name(line), line

                    if len(name): open_file = open_name.format(i, name)
                    else: raise Exception('Wrong format - Failed to get register name')

                elif j not in [1, len(lines) - 1]:
                    newnumber = get_number(line)
                    if len(newnumber): res_numbers += newnumber + '\n'
                    else: raise Exception('Wrong format - Failed to get value number')

            with open(newfilename, 'w') as dump:
                dump.write(res_numbers)

            newcontent = content[ : idx_start]
            newcontent += keep_line + '\n'
            newcontent += ' ' * get_padding(keep_line) + open_file + '\n'
            newcontent += content[idx_end :]

            with open('parsed_' + filename, 'w') as result: result.write(newcontent)

if __name__ == '__main__':
    parser('testcase.v')

    with open('expected_2.v', 'r') as file: string1 = file.read()

    with open('parsed_testcase.v', 'r') as file: string2 = file.read()

    assert string1 == string2
    print('Worked!')