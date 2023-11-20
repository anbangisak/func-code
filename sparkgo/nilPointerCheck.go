package main

import (
	"fmt"
)

type M3U8Entry struct {
	Tag    string
	Values string
}

type M3U8 struct {
	Entries []M3U8Entry
}

func (m *M3U8) Done() {
	for _, entry := range m.Entries {
		fmt.Println(entry.Tag)
	}
}

func main() {
	var val []string
	// val := []string{"a", "b"}
	fmt.Println(val)
}
