
CLIENT_OBJ=pel.c aes.c sha1.c shell.c
all:
	gcc -O3 -W -Wall -o pty $(CLIENT_OBJ)

clean:
	rm -f *.o client server pty