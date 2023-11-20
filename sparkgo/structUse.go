package main

import (
	"fmt"
)

type nila struct {
	sand     string
	islight  bool
	minerals []string
}

func main() {
	fmt.Println("nila test")
	n := nila{}
	n.islight = true
	n.minerals = append(n.minerals, "hai")
	n.sand = "white"
	fmt.Println(n)

	b := nila{islight: false, minerals: []string{"hai", "hello"}, sand: "black"}
	fmt.Println(b)
}
