#/usr/bin/python3
class Subject():
    def __init__(self, name):
        print("Subject is {0}".format(name))

class Science(Subject):
    def __init__(self, name):
        super().__init__(name)

obj = Science("Physics")