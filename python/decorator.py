#/usr/bin/python3
def hello(func):
    def wrapper():
        print("Hi Hello")
        return func
    return wrapper()

@hello
def hai(name):
    print("welcome {0}".format(name))

hai("guna")