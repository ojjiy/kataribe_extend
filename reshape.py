import os
import sys
import argparse
import glob
import copy

import parse
import termcolor


## Constants
TIMER_UNIT_DEF = "Timer unit: {unit:g} s"
TIMER_UNIT_LINE = 0
TOTAL_TIME_DEF = "Total time: {time:g} s"
TOTAL_TIME_LINE = 2
FILE_NAME_DEF = "File: {fname:S}"
FILE_NAME_LINE = 3
FUNC_NAME_DEF = "Function: {func_name:S}{:.}"
FUNC_NAME_LINE = 4
FUNC_LINE_DEF = "{:.}at line {line_num:d}"
FUNC_LINE_LINE = 4

COLUMN_NAME_LINE = 6
CODE_COLUMN_NAME = "Line Contents"


class FileInfo():
    def __init__(self, filename=None):
        self.filename = filename
        self.maxim_hits_digits = 9
        self.maxim_time_digits = 10

        if filename is None:
            return

        with open(filename) as f:
            data = f.readlines()

        self.unit = parse.parse(TIMER_UNIT_DEF, data[TIMER_UNIT_LINE])['unit']
        self.time = parse.parse(TOTAL_TIME_DEF, data[TOTAL_TIME_LINE])['time']
        self.fname = parse.parse(FILE_NAME_DEF, data[FILE_NAME_LINE])['fname']
        self.func_name = parse.parse(
            FUNC_NAME_DEF, data[FUNC_NAME_LINE])['func_name']
        self.line_num = parse.parse(
            FUNC_LINE_DEF, data[FUNC_LINE_LINE])['line_num']

        self.stats = {}
        self.code_offset = data[COLUMN_NAME_LINE].find(CODE_COLUMN_NAME)
        for l in (x.rstrip("\n") for x in data[8:]):
            if l == "":
                break
            chunk = l.split()
            line = int(chunk[0])
            self.stats[line] = {}
            if len(chunk) < 2:
                continue
            line_dict = parse.parse(
                "{hits:d}{:s}{time:f}{:s}{perhit:f}{:s}{ratio:f}{:s}{code}", " ".join(chunk[1:]))
            if line_dict is None:
                self.stats[line]['code'] = l[self.code_offset:]
                continue
            line_dict.named['code'] = l[self.code_offset:]
            self.stats[line] = line_dict.named
            self.maxim_hits_digits = max(self.maxim_hits_digits, len(
                str(self.stats[line]['hits'])))
            self.maxim_time_digits = max(self.maxim_time_digits, len(
                str(int(self.stats[line]['time']))))

    def isAddable(self, other):
        return self.unit == other.unit and self.fname == other.fname and self.func_name == other.func_name and self.line_num == other.line_num

    @staticmethod
    def colored(content, ratio):
        color_list = [
            (50, ['white', 'on_red'], ['bold']),
            (35, ['red'], ['bold']),
            (20, ['yellow'], ['bold']),
            (10, ['yellow'], []),
            (5, ['green'], []),
            (0, ['cyan'], []),
        ]
        for ratio_bound, args, attrs in color_list:
            if ratio >= ratio_bound:
                return termcolor.colored(content, *args, attrs=attrs)
        raise RuntimeError('Negative ratio is given: {}'.format(ratio))

    def save_txt(self, filename, colorize):
        with open(filename, 'w') as f:
            f.write("Timer unit: {} s\n\nTotal time: {} s\nFile: {}\nFunction: {} at line {}\n\n"
                    .format(self.unit, self.time, self.fname, self.func_name, self.line_num))
            f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  Line Contents\n"
                    .format(line_num="Line #", hits="Hits", hits_digits=self.maxim_hits_digits+1, time="Time", time_digits=self.maxim_time_digits+3, per_hit="Per Hit", ratio="% Time"))
            f.write("="*(6+9+9+self.maxim_time_digits +
                         self.maxim_hits_digits+4+15)+"\n")
            for line in self.stats.keys():
                code = self.stats[line]['code']+"\n" if 'code' in self.stats[line].keys() else "\n"
                if 'hits' in self.stats[line].keys():
                    ratio = self.stats[line]['ratio']
                    stats = "{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}.1f}{per_hit:>9.1f}{ratio:>9.1f}  ".format(line_num=line, hits=self.stats[line]['hits'], hits_digits=self.maxim_hits_digits+1, time=self.stats[line]['time'], time_digits=self.maxim_time_digits+3, per_hit=self.stats[line]['perhit'], ratio=self.stats[line]['ratio'])
                    if colorize:
                        stats = self.colored(stats, ratio)
                    f.write(stats)
                    f.write(code)
                else:
                    f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  {code}"
                            .format(line_num=line, hits="", hits_digits=self.maxim_hits_digits+1, time="", time_digits=self.maxim_time_digits+3, per_hit="", ratio="", code=code))

    def __add__(self, other):
        if not self.isAddable(other):
            raise AssertionError("Header information not match\n\t1. function: {} at line {} in file {} (time unit: {})\n\t2. function: {} at line {} in file {} (time unit: {})"
                                 .format(self.func_name, self.line_num, self.fname, self.unit, other.func_name, other.line_num, other.fname, other.unit))
        result = FileInfo()
        result.filename = self.filename
        result.maxim_hits_digits = max(
            self.maxim_hits_digits, other.maxim_hits_digits)
        result.maxim_time_digits = max(
            self.maxim_time_digits, other.maxim_hits_digits)
        result.unit = self.unit
        result.time = self.time + other.time
        result.fname = self.fname
        result.func_name = self.func_name
        result.line_num = self.line_num
        result.stats = {}
        for num in self.stats.keys():
            result.stats[num] = {}
            if len(self.stats[num]) == 0 or len(other.stats[num]) == 0:
                assert len(self.stats[num]) == len(
                    other.stats[num]), "Different source code detected at line {}".format(num)
                continue
            assert self.stats[num]['code'] == other.stats[num]['code'], "Different source code detected at line {}\n{:^30}| {}\n{:^30}| {}"\
                .format(num, self.filename, self.stats[num]['code'], other.filename, other.stats[num]['code'])
            result.stats[num]['code'] = self.stats[num]['code']
            if not 'hits' in self.stats[num].keys():
                continue
            result.stats[num]['hits'] = self.stats[num]['hits'] + \
                other.stats[num]['hits']
            result.maxim_hits_digits = max(result.maxim_hits_digits, len(
                str(result.stats[num]['hits'])))
            result.stats[num]['time'] = self.stats[num]['time'] + \
                other.stats[num]['time']
            result.maxim_time_digits = max(result.maxim_time_digits, len(
                str(int(result.stats[num]['time']))))
            result.stats[num]['perhit'] = result.stats[num]['time'] / \
                result.stats[num]['hits']
            result.stats[num]['ratio'] = result.stats[num]['time'] * \
                result.unit * 100 / result.time
        result.code_offset = 31 + self.maxim_hits_digits + self.maxim_time_digits
        return result

    def __radd__(self, other):
        if other == 0:
            return self
        return self.__add__(other)


def main(paths, use_color):
    targets = []
    for path in paths:
        if os.path.isdir(path):
            for item in glob.glob(os.path.join(path, '**'), recursive=True):
                targets.append(item)
        else:
            targets.append(path)
    targets = [t for t in targets if os.path.splitext(t)[1] == '.txt']

    if len(targets) == 0:
        print('No target file detected.')
        return

    print('Process following {} files: '.format(len(targets)))
    print('\n'.join(['\t{}'.format(f) for f in targets]))

    total = sum(map(FileInfo, targets))
    total.save_txt('result.txt', use_color)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'files', nargs='*', default=['.'],
        help='Specify folders/files to be aggregated. When folder is '
        'specified, all text files below the folder are specified')
    parser.add_argument(
        '--color', action='store_true',
        help="colorize result with ANSI escape code")
    args = parser.parse_args()

    main(args.files, args.color)
