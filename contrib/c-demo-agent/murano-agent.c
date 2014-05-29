#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <string.h>
#include <stdint.h>
#include <assert.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>

#include <amqp_tcp_socket.h>
#include <amqp.h>
#include <amqp_framing.h>

#include "utils.h"
#include "lcfg_static.h"


static void run ( amqp_connection_state_t conn, int log_fd , const char *result_routing_key )
{
    int received = 0;
    amqp_frame_t frame;

    while ( 1 )
    {
        amqp_rpc_reply_t ret;
        amqp_envelope_t envelope;

        amqp_maybe_release_buffers ( conn );
        ret = amqp_consume_message ( conn, &envelope, NULL, 0 );

        if ( AMQP_RESPONSE_NORMAL == ret.reply_type )
        {
            int i;
            amqp_bytes_t body = envelope.message.body;
            const char *title = "A new message received:\n";

            fprintf ( stdout, title, received );
            for ( i = 0; i < body.len; i++ )
            {
                fprintf ( stdout, "%c", * ( char* ) ( body.bytes + i ) );
            }
            puts ( "\n" );

            write ( log_fd, ( void * ) title, strlen ( title ) );
            write ( log_fd, body.bytes, body.len );
            write ( log_fd, ( void * ) "\n\n", 2 );

	    /* Send a reply. */
            amqp_basic_properties_t props;
            props._flags = AMQP_BASIC_CONTENT_TYPE_FLAG | AMQP_BASIC_DELIVERY_MODE_FLAG  | AMQP_BASIC_MESSAGE_ID_FLAG;
	    
	    printf("message id: %s", (const char*)envelope.message.properties.message_id.bytes);
	    
            props.message_id = amqp_bytes_malloc_dup ( envelope.message.properties.message_id );
            props.content_type = amqp_cstring_bytes ( "text/json" );
            props.delivery_mode = 2; /* persistent delivery mode */

            const char *result_body = "{\"IsException\": false, \"Result\": [{\"IsException\": false, \"Result\": []}]}";

            die_on_error ( amqp_basic_publish ( conn,
                                                1,
                                                amqp_cstring_bytes ( "" ),
                                                amqp_cstring_bytes ( result_routing_key ),
                                                0,
                                                0,
                                                &props,
                                                amqp_cstring_bytes ( result_body ) ),
			   "Publishing" );

            amqp_destroy_envelope ( &envelope );
        }
        else
        {
            if ( AMQP_RESPONSE_LIBRARY_EXCEPTION == ret.reply_type &&
                    AMQP_STATUS_UNEXPECTED_STATE == ret.library_error )
            {
                if ( AMQP_STATUS_OK != amqp_simple_wait_frame ( conn, &frame ) )
                {
                    return;
                }

                if ( AMQP_FRAME_METHOD == frame.frame_type )
                {
                    switch ( frame.payload.method.id )
                    {
                    case AMQP_BASIC_ACK_METHOD:
                        /* if we've turned publisher confirms on, and we've published a message
                         * here is a message being confirmed
                         */

                        break;
                    case AMQP_BASIC_RETURN_METHOD:
                        /* if a published message couldn't be routed and the mandatory flag was set
                         * this is what would be returned. The message then needs to be read.
                         */
                    {
                        amqp_message_t message;
                        ret = amqp_read_message ( conn, frame.channel, &message, 0 );

                        if ( AMQP_RESPONSE_NORMAL != ret.reply_type )
                        {
                            return;
                        }

                        amqp_destroy_message ( &message );
                    }

                    break;

                    case AMQP_CHANNEL_CLOSE_METHOD:
                        /* a channel.close method happens when a channel exception occurs, this
                         * can happen by publishing to an exchange that doesn't exist for example
                         *
                         * In this case you would need to open another channel redeclare any queues
                         * that were declared auto-delete, and restart any consumers that were attached
                         * to the previous channel
                         */
                        return;

                    case AMQP_CONNECTION_CLOSE_METHOD:
                        /* a connection.close method happens when a connection exception occurs,
                         * this can happen by trying to use a channel that isn't open for example.
                         *
                         * In this case the whole connection must be restarted.
                         */
                        return;

                    default:
                        fprintf ( stderr ,"An unexpected method was received %d\n", frame.payload.method.id );
                        return;
                    }
                }
            }

        }

        received++;
    }
}

static const char* get_config_value ( struct lcfg *cfg, const char *key, int verbose )
{
    void *data;
    size_t len;

    if ( lcfg_value_get ( cfg, key, &data, &len ) != lcfg_status_ok )
    {
        fprintf ( stderr, "Key %s is not found in the configuration file", key );
    }

    const char *val = ( const char * ) data;

    if ( verbose )
    {
        fprintf ( stdout, "%s = %s\n", key, val );
    }

    return val;
}

int main ( int argc, char const *const *argv )
{
    if ( argc != 3 )
    {
        printf ( "usage: %s CFG_FILE LOG_FILE\n", argv[0] );

        return -1;
    }

    const char *log_filename = argv[2];
    int flags = O_CREAT | O_APPEND | O_RDWR;
    mode_t mode = S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP;
    int log_fd = open ( log_filename, flags, mode );

    if ( log_fd < 0 )
    {
        fprintf ( stderr, "ERROR: Falied to open the log file '%s'\n", log_filename );

        exit ( 1 );
    }

    /* Read the configuration file. */
    struct lcfg *cfg = lcfg_new ( argv[1] );

    if ( lcfg_parse ( cfg ) != lcfg_status_ok )
    {
        printf ( "lcfg error: %s\n", lcfg_error_get ( cfg ) );

        return -1;
    }

    /* Read all the configuration parameters. */
    fprintf ( stdout, "Starting Murano agent with the following configuration:\n\n" );

    const char *host = get_config_value ( cfg, "RABBITMQ_HOST" , 1 );
    int port = atoi ( get_config_value ( cfg, "RABBITMQ_PORT" , 1 ) );
    const char *vhost = get_config_value ( cfg, "RABBITMQ_VHOST"  , 1 );
    const char *username = get_config_value ( cfg, "RABBITMQ_USERNAME"  , 1 );
    const char *password = get_config_value ( cfg, "RABBITMQ_PASSWORD"  , 1 );
    const char *queuename = get_config_value ( cfg, "RABBITMQ_INPUT_QUEUE"  , 1 );
    const char *result_routing_key = get_config_value ( cfg, "RABBITMQ_RESULT_ROUTING_KEY", 1 );

    amqp_connection_state_t conn = amqp_new_connection();
    amqp_socket_t *socket = NULL;
    amqp_bytes_t queuename_bytes = amqp_cstring_bytes ( queuename );

    socket = amqp_tcp_socket_new ( conn );
    if ( !socket )
    {
        die ( "creating TCP socket" );
    }

    if ( amqp_socket_open ( socket, host, port ) )
    {
        die ( "opening TCP socket" );
    }

    die_on_amqp_error ( amqp_login ( conn, vhost, 0, 131072, 0, AMQP_SASL_METHOD_PLAIN, username, password ),
                        "Logging in" );
    amqp_channel_open ( conn, 1 );
    die_on_amqp_error ( amqp_get_rpc_reply ( conn ), "Opening channel" );

    amqp_basic_consume ( conn, 1, queuename_bytes, amqp_empty_bytes, 0, 1, 0, amqp_empty_table );
    die_on_amqp_error ( amqp_get_rpc_reply ( conn ), "Consuming" );

    puts ( "\nSuccessfully connected to Rabbit MQ server! Ready for messages..." );

    run ( conn, log_fd , result_routing_key );

    close ( log_fd );
    lcfg_delete ( cfg );

    die_on_amqp_error ( amqp_channel_close ( conn, 1, AMQP_REPLY_SUCCESS ), "Closing channel" );
    die_on_amqp_error ( amqp_connection_close ( conn, AMQP_REPLY_SUCCESS ), "Closing connection" );
    die_on_error ( amqp_destroy_connection ( conn ), "Ending connection" );

    return 0;
}
