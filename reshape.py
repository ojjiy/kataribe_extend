import argparse
import copy
import glob
import os

import parse
import termcolor


class LineInfo():
    def __init__(self, code, hits=0, time=0):
        self.code = code
        self.hits = hits
        self.time = time

    def __iadd__(self, other):
        assert self.code == other.code  # TODO: error message
        self.hits += other.hits
        self.time += other.time
        return self


class FileInfo():
    def __init__(self, filename):
        with open(filename) as f:
            data = f.readlines()

        summary = parse.parse(
            'Timer unit: {unit:g} s\n'
            '\n'
            'Total time: {time:g} s\n'
            'File: {fname:S}\n'
            'Function: {func_name:S} at line {line_num:d}\n',
            ''.join(data[:5]))
        self.unit = summary['unit']
        self.time = summary['time']
        self.fname = summary['fname']
        self.func_name = summary['func_name']
        self.line_num = summary['line_num']

        self.stats = {}
        code_offset = data[6].find('Line Contents')
        for l in (x.rstrip("\n") for x in data[8:]):
            if l == "":
                break
            chunk = l.split()
            line = int(chunk[0])
            line_dict = parse.parse(
                "{hits:d}{:s}{time:f}{:s}{perhit:f}{:s}{ratio:f}{:s}{code}", " ".join(chunk[1:]))

            code = l[code_offset:]
            if line_dict is None:
                self.stats[line] = LineInfo(code)
            else:
                self.stats[line] = LineInfo(code, line_dict.named['hits'], line_dict.named['time'])

    def check_addable(self, other):
        assert self.unit == other.unit  # TODO: Fix
        assert self.fname == other.fname
        assert self.func_name == other.func_name
        assert self.line_num == other.line_num

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

    def save_txt(self, f, use_color):
        maxim_hits_digits = 9
        maxim_time_digits = 10
        for line_no in self.stats.keys():
            maxim_hits_digits = max(maxim_hits_digits, len(str(self.stats[line_no].hits)))
            maxim_time_digits = max(maxim_time_digits, len(str(self.stats[line_no].time)))

        f.write('Timer unit: {} s\n\n'.format(self.unit))
        f.write('Total time: {} s\n'.format(self.time))
        f.write('File: {}\n'.format(self.fname))
        f.write('Function: {} at line {}\n\n'.format(
            self.func_name, self.line_num))
        f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  Line Contents\n"
                .format(line_num="Line #", hits="Hits", hits_digits=maxim_hits_digits+1, time="Time", time_digits=maxim_time_digits+3, per_hit="Per Hit", ratio="% Time"))
        f.write("="*(6+9+9+maxim_time_digits + maxim_hits_digits+4+15)+"\n")

        for line_no in self.stats.keys():
            stats = self.stats[line_no]
            code = stats.code
            if stats.hits > 0:
                ratio = stats.time / self.time * self.unit * 100
                perhit = stats.time / stats.hits
                stats_str = "{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}.1f}{per_hit:>9.1f}{ratio:>9.1f}  ".format(
                    line_num=line_no, hits=stats.hits, hits_digits=maxim_hits_digits+1,
                    time=stats.time, time_digits=maxim_time_digits+3,
                    per_hit=perhit, ratio=ratio)
                if use_color:
                    stats_str = self.colored(stats_str, ratio)
                f.write(stats_str)
                f.write(code + '\n')
            else:
                f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  {code}\n"
                        .format(line_num=line_no, hits="", hits_digits=maxim_hits_digits+1, time="", time_digits=maxim_time_digits+3, per_hit="", ratio="", code=code))

    def __iadd__(self, other):
        self.check_addable(other)
        self.time += other.time
        assert self.stats.keys() == other.stats.keys()  # TODO: error message

        for line_no in self.stats.keys():
            self.stats[line_no] += other.stats[line_no]
        return self

    def __add__(self, other):
        if not other:
            return self
        result = copy.copy(self)
        result.stats = copy.copy(result.stats)
        result += other
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
    with open('result.txt', 'w') as f:
        total.save_txt(f, use_color)


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
