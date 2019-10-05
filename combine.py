import argparse
import copy
import glob
import os

import parse
import termcolor


class LineInfo():
    def __init__(self, code, hits, time):
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
        if summary is None:
            raise RuntimeError('Wrong header in file {}'.format(filename))
        self.unit = summary['unit']
        self.overall_time = summary['time']
        self.fname = summary['fname']
        self.func_name = summary['func_name']
        self.line_num = summary['line_num']
        code_offset = data[6].find('Line Contents')

        self.stats = {}
        for line in data[8:]:
            line = line.rstrip()
            code = line[code_offset:]
            chunk = [s for s in line[:code_offset].split(' ') if s != '']

            if len(chunk) == 0:
                continue
            elif len(chunk) == 1:
                line_no, hits, time = chunk[0], 0, 0
            elif len(chunk) == 5:
                line_no, hits, time = chunk[:3]
            else:
                raise RuntimeError('Wrong format: {}'.format(line))

            self.stats[int(line_no)] = LineInfo(code, int(hits), float(time))

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

    def formatted(self, line_num, hits_width, time_width, use_color):
        stats = self.stats[line_num]
        if stats.hits > 0:
            hits = stats.hits
            time = stats.time
            per_hit = round(stats.time / stats.hits, 1)
            ratio = round(stats.time / self.overall_time * self.unit * 100, 1)
        else:
            hits = ''
            time = ''
            per_hit = ''
            ratio = ''
        formatted_stat = '{line_num:>6}{hits:>{hits_width}}{time:>{time_width}}{per_hit:>9}{ratio:>9}'.format(
                    line_num=line_num,
                    hits=hits,
                    hits_width=hits_width,
                    time=time,
                    time_width=time_width,
                    per_hit=per_hit,
                    ratio=ratio)
        if use_color and stats.hits > 0:
            formatted_stat = self.colored(formatted_stat, ratio)
        formatted_stat += '  {code}'.format(code=stats.code)
        return formatted_stat

    def show_result(self, use_color):
        maxim_hits_digits = 9
        maxim_time_digits = 12
        for line_no in self.stats.keys():
            maxim_hits_digits = max(maxim_hits_digits,
                                    len(str(self.stats[line_no].hits)))
            maxim_time_digits = max(maxim_time_digits,
                                    len(str(self.stats[line_no].time)))

        hits_width = maxim_hits_digits+1
        time_width = maxim_time_digits+1

        print('Timer unit: {} s\n'.format(self.unit))
        print('Total time: {} s'.format(self.overall_time))
        print('File: {}'.format(self.fname))
        print('Function: {} at line {}\n'.format(
            self.func_name, self.line_num))
        print('{line_num:>6}'
                          '{hits:>{hits_digits}}'
                          '{time:>{time_digits}}'
                          '{per_hit:>9}'
                          '{ratio:>9}'
                          '  Line Contents\n'.format(line_num='Line #',
                                                     hits='Hits',
                                                     hits_digits=hits_width,
                                                     time='Time',
                                                     time_digits=time_width,
                                                     per_hit='Per Hit',
                                                     ratio='% Time'))
        print('='*80)

        for line_num in self.stats.keys():
            print(self.formatted(line_num, hits_width, time_width, use_color))

    def __iadd__(self, other):
        self.check_addable(other)
        self.overall_time += other.overall_time
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
    print('-'*80)

    total = sum(map(FileInfo, targets))
    total.show_result(use_color)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'files', nargs='*', default=['.'],
        help='Specify folders/files to be aggregated. When folder is '
        'specified, all text files below the folder are specified')
    parser.add_argument(
        '--color', action='store_true',
        help='colorize result with ANSI escape code')
    args = parser.parse_args()

    main(args.files, args.color)
