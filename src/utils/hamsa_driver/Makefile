# Find here an example of how to compile src/cpp/main.cpp
# This uses the firmware purely in cpp, without binding to python

INCLUDE = -I src/cpp
CFLAGS = -O3 -Wall -Werror $(INCLUDE)

CPP_SRC = $(shell find src/cpp -type f \( -iname "*.cpp" ! -iname "main.cpp" \) )
CPP_OBJ = $(patsubst src/cpp/%.cpp, .build/cpp/%.o, $(CPP_SRC))

BINARY = make_go

$(BINARY) : $(CPP_OBJ) src/cpp/main.cpp
	$(CXX) $(CFLAGS) -o $@ $^

.build/cpp/%.o: src/cpp/%.cpp
	mkdir -p $(dir $@)
	$(CXX) -c $(CFLAGS) -o $@ $<

clean :
	rm -rf .build $(BINARY)

.PHONY : clean
