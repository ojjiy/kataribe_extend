import os
import sys
import argparse
import glob
import parse

def parse_file(file):
  file_info = {}
  with open(file) as f:
    data = f.readlines()
  file_info['unit'] = parse.parse("Timer unit: {:g} s", data[0])[0]
  file_info['time'] = parse.parse("Total time: {:g} s", data[2])[0]
  file_info['fname'] = parse.parse("File: {:S}", data[3])[0]
  file_info['func_name'] = parse.parse("Function: {:S} at line {:d}", data[4])[0]
  file_info['line_num'] = parse.parse("Function: {:S} at line {:d}", data[4])[1]

  file_info['res'] = {}
  for l in (x.strip() for x in data[8:]):
    if l=="":
      break
    chunk = l.split()
    line = int(chunk[0])
    file_info['res'][line] = {}
    if len(chunk)<2:
      continue
    line_dict = parse.parse("{hits:d}{:s}{time:f}{:s}{perhit:f}{:s}{ratio:f}{:s}{code}", " ".join(chunk[1:]))
    if line_dict is None:
      file_info['res'][line]['code'] = " ".join(chunk[1:])
      continue
    file_info['res'][line] = line_dict.named
  return file_info

def merge_file(*files):
  if len(files) == 1:
    return files[0]
  res = parse_file(files[0])
  for f in files[1:]:
    target = parse_file(f)
    assert res['unit'] == target['unit'] and res['fname'] == target['fname'] and res['func_name'] == target['func_name'] and res['line_num'] == target['line_num'],\
       "Header information not match\n\t1. function: {} at line {} in file {} (time unit: {})\n\t2. function: {} at line {} in file {} (time unit: {})"\
         .format(res['func_name'], res['line_num'], res['fname'], res['unit'], target['func_name'], target['line_num'], target['fname'], target['unit'])
    res['time'] += target['time']
    for num in res['res'].keys():
      if len(res['res'][num])==0 or len(target['res'][num])==0:
        assert len(res['res'][num])==len(target['res'][num]), "Different source code detected at line {}".format(num)
        continue
      assert res['res'][num]['code'] == target['res'][num]['code'], "Different source code detected at line {}\n1. {}\n2. {}"\
        .format(num, res['res'][num]['code'], target['res'][num]['code'])
      res['res'][num]['hits'] += target['res'][num]['hits']
      res['res'][num]['time'] += target['res'][num]


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
  for f in target:
    print("\t{}".format(f))
  merge_file(*target)

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