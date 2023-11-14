class App(object):
    a = 70
    b = 60
    def __init__(self):
        self.a = 77

    def setBval(self):
        self.a = 71

class Misa(object):
    a = 80
    b = 50

    def setBval(self):
        self.a = 88

class Letter(Misa, App):
    pass

c = Letter()
print(c.a, c.b)
c.setBval()
print(c.a, c.b)
