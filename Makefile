
CLIENT_OBJ=pel.c aes.c sha1.c shell.c
CLIENT_TEST_OBJ=pel.c aes.c sha1.c client.c
SERVER_TEST_OBJ=pel.c aes.c sha1.c server.c
all:
	gcc -O3 -W -Wall -o pty $(CLIENT_OBJ)
	gcc -O3 -W -Wall -o client $(CLIENT_TEST_OBJ)
	gcc -O3 -W -Wall -o server $(SERVER_TEST_OBJ)

clean:
	rm -f *.o client server pty