/*
package main

import fmt

func point() {
	i, j := 42, 2701
	p, q := &i, &j
	*p, q = 21, 42
	fmt.Println(*p, *q, i, j)
}

func main() {
	point()
}
*/
package main

import "fmt"

func point() {
	i, j := 42, 2701
	p, q := &i, &j
	*p, *q = 21, 42
	fmt.Println(*p, *q, i, j)
}

func main() {
	point()
}
