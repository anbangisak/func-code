#/usr/bin/python3
def run(n):
    for i in range(0, n):
        yield i

trigger = run(3)
print(next(trigger))
print(next(trigger))