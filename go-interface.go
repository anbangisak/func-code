package main

import "fmt"

type scale interface {
	area()
}

type circle struct {
	radius uint
}

func (c circle) area() {
	fmt.Println(c.radius * 2)
}

type square struct {
	radius uint
}

func (s square) area() {
	fmt.Println(s.radius * 4)
}

func display(s scale) {
	s.area()
	fmt.Println("hello")
}

func main() {
	c := circle{radius: 3}
	display(c)
}
