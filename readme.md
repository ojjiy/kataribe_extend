## What this file can
Aggregate statistics of execution time analyzed using greatest tool [line_profiler](https://github.com/rkern/line_profiler).

## Benefit
- Unite multi-thread result
- Unite repetitive result without modification to source code

## Usage
```bash
$ python3 ./reshape.py [files to be aggregated] [folders which contain files to be aggregated] [--color]
```

## Verification
```bash
$ python3 ./reshape.py ./inputs --colorize
$ less ./result.txt
```

## Change
### 1.0
initial release
