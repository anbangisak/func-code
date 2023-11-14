class App(object):
    a = 70
    def __init__(self, b):
        self.b = b

# class Letter(App):
#     pass

class Letter(App):
    def __init__(self):
        super().__init__(10)

c = Letter()
print(c.a)

