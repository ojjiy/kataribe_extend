import os
import sys
import argparse
import glob
import parse
import copy

class FileInfo():
  def __init__(self, filename=None):
    self.content = {}
    self.filename=filename
    self.maxim_hits_digits = 9
    self.maxim_time_digits = 10
    if filename is not None:
      with open(filename) as f:
        data = f.readlines()
      self.content['unit'] = parse.parse("Timer unit: {:g} s", data[0])[0]
      self.content['time'] = parse.parse("Total time: {:g} s", data[2])[0]
      self.content['fname'] = parse.parse("File: {:S}", data[3])[0]
      self.content['func_name'] = parse.parse("Function: {:S} at line {:d}", data[4])[0]
      self.content['line_num'] = parse.parse("Function: {:S} at line {:d}", data[4])[1]

      self.content['res'] = {}
      for l in (x.strip() for x in data[8:]):
        if l=="":
          break
        chunk = l.split()
        line = int(chunk[0])
        self.content['res'][line] = {}
        if len(chunk)<2:
          continue
        line_dict = parse.parse("{hits:d}{:s}{time:f}{:s}{perhit:f}{:s}{ratio:f}{:s}{code}", " ".join(chunk[1:]))
        if line_dict is None:
          self.content['res'][line]['code'] = " ".join(chunk[1:])
          continue
        self.content['res'][line] = line_dict.named
        self.maxim_hits_digits = max(self.maxim_hits_digits, len(str(self.content['res'][line]['hits'])))
        self.maxim_time_digits = max(self.maxim_time_digits, len(str(int(self.content['res'][line]['time']))))

  def isAddable(self, other):
    return self.content['unit'] == other.content['unit'] and self.content['fname'] == other.content['fname'] and self.content['func_name'] == other.content['func_name'] and self.content['line_num'] == other.content['line_num']

  def colorize(self):
    CRITICAL = "\e[37;41;1m" # 50% -
    V_HEAVY = "\e[31;1m" # 35% - 50%
    HEAVY = "\e[33;1m" # 20% - 35%
    L_HEAVY = "\e[33m" # 10% - 20%
    NORMAL = "\e[32m" # 5% - 10%
    LIGHT = "\e[36m" # - 5%
    RESET = "\e[m"

  def save_txt(self, filename):
    with open(filename, 'w') as f:
      f.write("Timer unit: {} s\n\nTotal time: {} s\nFile: {}\nFunction: {} at line {}\n\n"\
        .format(self.content['unit'], self.content['time'], self.content['fname'], self.content['func_name'], self.content['line_num']))
      f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  Line Contents\n"\
        .format(line_num="Line #", hits="Hits", hits_digits=self.maxim_hits_digits+1, time="Time", time_digits=self.maxim_time_digits+3, per_hit="Per Hit", ratio="% Time"))
      f.write("="*(6+9+9+self.maxim_time_digits+self.maxim_hits_digits+4+15)+"\n")
      with open(self.content['fname'], 'r') as f2:
        src = f2.readlines()
      for line in self.content['res'].keys():
        if 'hits' in self.content['res'][line].keys():

          f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}.1f}{per_hit:>9.1f}{ratio:>9.1f}  {code}"\
            .format(line_num=line, hits=self.content['res'][line]['hits'], hits_digits=self.maxim_hits_digits+1, time=self.content['res'][line]['time'], time_digits=self.maxim_time_digits+3, per_hit=self.content['res'][line]['perhit'], ratio=self.content['res'][line]['ratio'], code=src[line-1]))
        else:
          f.write("{line_num:>6}{hits:>{hits_digits}}{time:>{time_digits}}{per_hit:>9}{ratio:>9}  {code}"\
            .format(line_num=line, hits="", hits_digits=self.maxim_hits_digits+1, time="", time_digits=self.maxim_time_digits+3, per_hit="", ratio="", code=src[line-1]))

  def __add__(self, other):
    if not self.isAddable(other):
      raise AssertionError("Header information not match\n\t1. function: {} at line {} in file {} (time unit: {})\n\t2. function: {} at line {} in file {} (time unit: {})"\
                             .format(self.content['func_name'], self.content['line_num'], self.content['fname'], self.content['unit'], other.content['func_name'], other.content['line_num'], other.content['fname'], other.content['unit']))
    result = FileInfo()
    result.filename = self.filename
    result.maxim_hits_digits = max(self.maxim_hits_digits, other.maxim_hits_digits)
    result.maxim_time_digits = max(self.maxim_time_digits, other.maxim_hits_digits)
    result.content['unit'] = self.content['unit']
    result.content['time'] = self.content['time']+other.content['time']
    result.content['fname'] = self.content['fname']
    result.content['func_name'] = self.content['func_name']
    result.content['line_num'] = self.content['line_num']
    result.content['res'] = {}
    for num in self.content['res'].keys():
      result.content['res'][num] = {}
      if len(self.content['res'][num])==0 or len(other.content['res'][num])==0:
        assert len(self.content['res'][num])==len(other.content['res'][num]), "Different source code detected at line {}".format(num)
        continue
      assert self.content['res'][num]['code'] == other.content['res'][num]['code'], "Different source code detected at line {}\n{:^30}| {}\n{:^30}| {}"\
        .format(num, self.filename, self.content['res'][num]['code'], other.filename, other.content['res'][num]['code'])
      result.content['res'][num]['code'] = self.content['res'][num]['code']
      if not 'hits' in self.content['res'][num].keys():
        continue
      result.content['res'][num]['hits'] = self.content['res'][num]['hits'] + other.content['res'][num]['hits']
      result.maxim_hits_digits = max(result.maxim_hits_digits, len(str(result.content['res'][num]['hits'])))
      result.content['res'][num]['time'] = self.content['res'][num]['time'] + other.content['res'][num]['time']
      result.maxim_time_digits = max(result.maxim_time_digits, len(str(int(result.content['res'][num]['time']))))
      result.content['res'][num]['perhit'] = result.content['res'][num]['time'] / result.content['res'][num]['hits']
      result.content['res'][num]['ratio'] = result.content['res'][num]['time'] * result.content['unit'] * 100 / result.content['time']
    return result

  def __radd__(self, other):
    if other==0:
      return self
    return self.__add__(other)

def main(cand):
  target = []
  for item in cand:
    if os.path.isfile(item) and os.path.splitext(item)[1] == ".txt":
      target.append(item)
    elif os.path.isdir(item):
      target += findtxt_recursive(item)
  if len(target)==0:
    print("No target file detected. Abort.")
    exit(0)
  print("Process following {} files: ".format(len(target)))
  contents=[]
  for f in target:
    print("\t{}".format(f))
    contents.append(FileInfo(f))
  total = sum(contents)
  total.save_txt('result.txt')

def findtxt_recursive(path):
  res = []
  for item in glob.glob(os.path.join(path, '*')):
    if os.path.isdir(item):
      res += findtxt_recursive(item)
    elif os.path.isfile(item) and os.path.splitext(item)[1] == ".txt":
      res.append(item)
    else:
      print("info: {} is ignored", item)
  return res


if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('files', nargs='*', help="Specify folders/files to be aggregated. When folder is specified, all text files below the folder are specified")
  args = parser.parse_args()
  main(args.files)