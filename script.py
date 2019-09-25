import line_profiler

pr = line_profiler.LineProfiler()

@pr
def f(x):
    s = 0
    for i in range(x):
        s += i
    return s

if __name__ == '__main__':
    print(f(1000000))
    print(f(1000000))
    print(f(1000000))
    with open('perf3.txt', 'w') as stream:
        pr.print_stats(stream=stream)