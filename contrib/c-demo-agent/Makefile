# Makefile for murano agent

CFLAGS= -Wall

default_target: all
	

all: agent-binary producer-binary
	

# NOTE: Use this if RabbitMQ needs to be linked in as a dynamic library
#agent-binary: murano-agent.o lcfg_static.o utils.o
#	gcc -o murano-agent murano-agent.o lcfg_static.o utils.o -lrabbitmq -lrt

agent-binary: murano-agent.o lcfg_static.o utils.o librabbitmq.a
	gcc $(CFLAGS) -o murano-agent murano-agent.o lcfg_static.o utils.o -L. -lrabbitmq -lrt

# NOTE: Use this if RabbitMQ needs to be linked in as a dynamic library
#producer-binary: producer.o utils.o
#	gcc -o producer producer.o utils.o -lrabbitmq -lrt

producer-binary: producer.o utils.o librabbitmq.a
	gcc $(CFLAGS) -o producer producer.o utils.o -L. -lrabbitmq -lrt

murano-agent.o: murano-agent.c
	gcc $(CFLAGS) -c -I. -fPIC murano-agent.c

producer.o: producer.c
	gcc $(CFLAGS) -c -I. -fPIC producer.c

lcfg_static.o: lcfg_static.c
	gcc $(CFLAGS) -c -fPIC lcfg_static.c

utils.o: utils.c
	gcc $(CFLAGS) -c -I. -fPIC utils.c

clean:
	rm -f *.o murano-agent producer
