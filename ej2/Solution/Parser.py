import re

regex = re.compile(r'  reg \[(.*)\] (\S*) \[(.*)\];\n  initial begin\n((    \S*\[\S*\] = \S*;\n)*)  end\n')

def get_reg_name(definition : str) -> str:
    """ Gets register name from its definition """

    start_name = definition.find(']')
    end_name = definition.rfind('[')

    if start_name != -1 and end_name != -1:
        return definition[start_name + 1 : end_name].strip()

    else: return ''

def get_number(value_line : str) -> '':
    """ Gets the number assigned to a given position """

    init_pos = value_line.find("'")

    if init_pos != -1:
        return value_line[init_pos + 2 : -1]

    return ''

def get_padding(line : str) -> int:
    """ Gets horizontal position of line """

    i = 0
    while i < len(line) and line[i] == ' ': i += 1
    return i

def parser(filename : str) -> None:
    """ Parses Verilog file to transform invalid syntax into a valid one """

    with open(filename, 'r+') as file:

        idx_path = filename.rfind('/')

        content = file.read()
        dump_name = 'memdump{}.mem'
        open_command = '$readmemh("memdump{}.mem", {});\n'

        for i, match in enumerate(re.finditer(regex, content)):
            string = match.group()

            dump_name_i = dump_name.format(i)
            res_numbers = ''

            # Loops through every line of the string to replace
            lines = string.splitlines()
            for j, line in enumerate(lines):

                # The first line defines the register, so we get the register's name and keep the whole line
                if not j:
                    name, keep_line = get_reg_name(line), line + '\n'

                    if len(name): open_command_i = open_command.format(i, name)
                    else: raise ValueError(f"Wrong format - Failed to get register's name at line {j + 1} of case {i + 1}")

                # Except for the second (1) and last (len(lines) - 1) lines, the rest of them have
                # the actual numbers to move to the dumpfile. We get those numbers and save them in
                # res_numbers for future dumping to memory
                elif j not in [1, len(lines) - 1]:
                    newnumber = get_number(line)

                    if len(newnumber): res_numbers += newnumber + '\n'
                    else: raise ValueError('Wrong format - Failed to get value at line {j + 1} of case {i + 1}"')

            # Saves dumpfile output
            with open(filename[ : idx_path + 1] + dump_name_i, 'w') as dump: dump.write(res_numbers)

            # Replaces original content with new syntax
            replacement = keep_line + ' ' * get_padding(keep_line) + open_command_i
            content = content.replace(string, replacement)

        # Finally, saves the output to a new file
        with open(filename[ : idx_path + 1] + 'parsed_' + filename[idx_path + 1 : ], 'w') as result:
            result.write(content)

def test(file_in : str, expected : str) -> bool:
    parser(file_in)
    idx_path = file_in.find('/')

    with open(expected, 'r') as file: string1 = file.read()

    with open(file_in[ : idx_path + 1] + 'parsed_' + file_in[idx_path + 1 : ], 'r') as file:
        string2 = file.read()

    return string1 == string2

if __name__ == '__main__':
    print(f'Worked: {test("Data/new_testcase.v", "Data/new_expected.v")}')

