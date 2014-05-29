
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include <stdint.h>
#include <amqp_tcp_socket.h>
#include <amqp.h>
#include <amqp_framing.h>

#include "utils.h"

#define SUMMARY_EVERY_US 1000000

static void send_batch ( amqp_connection_state_t conn,
                         char const *queue_name,
                         int rate_limit,
                         int message_count )
{
    uint64_t start_time = now_microseconds();
    int i;
    int sent = 0;
    int previous_sent = 0;
    uint64_t previous_report_time = start_time;
    uint64_t next_summary_time = start_time + SUMMARY_EVERY_US;

    const char *message = "Hello from the producer!";
    amqp_bytes_t message_bytes;

    message_bytes.len = strlen ( message );
    message_bytes.bytes = ( void * ) message;

    for ( i = 0; i < message_count; i++ )
    {
        uint64_t now = now_microseconds();

        amqp_basic_properties_t props;
        props._flags = AMQP_BASIC_CONTENT_TYPE_FLAG | AMQP_BASIC_DELIVERY_MODE_FLAG | AMQP_BASIC_MESSAGE_ID_FLAG;
        props.message_id = amqp_cstring_bytes( " msg_id " );
        props.content_type = amqp_cstring_bytes ( "text/json" );
        props.delivery_mode = 2; /* persistent delivery mode */

        die_on_error ( amqp_basic_publish ( conn,
                                            1,
                                            amqp_cstring_bytes ( "" ),
                                            amqp_cstring_bytes ( queue_name ),
                                            0,
                                            0,
                                            &props,
                                            message_bytes ),
                       "Publishing" );
        sent++;
        if ( now > next_summary_time )
        {
            int countOverInterval = sent - previous_sent;
            double intervalRate = countOverInterval / ( ( now - previous_report_time ) / 1000000.0 );
            printf ( "%d ms: Sent %d - %d since last report (%d Hz)\n",
                     ( int ) ( now - start_time ) / 1000, sent, countOverInterval, ( int ) intervalRate );

            previous_sent = sent;
            previous_report_time = now;
            next_summary_time += SUMMARY_EVERY_US;
        }

        while ( ( ( i * 1000000.0 ) / ( now - start_time ) ) > rate_limit )
        {
            microsleep ( 2000 );
            now = now_microseconds();
        }
    }

    {
        uint64_t stop_time = now_microseconds();
        int total_delta = stop_time - start_time;

        printf ( "PRODUCER - Message count: %d\n", message_count );
        printf ( "Total time, milliseconds: %d\n", total_delta / 1000 );
        printf ( "Overall messages-per-second: %g\n", ( message_count / ( total_delta / 1000000.0 ) ) );
    }
}

int main ( int argc, char const *const *argv )
{
    char const *hostname;
    int port, status;
    int rate_limit;
    int message_count;
    amqp_socket_t *socket = NULL;
    amqp_connection_state_t conn;

    if ( argc < 5 )
    {
        fprintf ( stderr, "Usage: producer host port rate_limit message_count\n" );
        return 1;
    }

    hostname = argv[1];
    port = atoi ( argv[2] );
    rate_limit = atoi ( argv[3] );
    message_count = atoi ( argv[4] );

    conn = amqp_new_connection();

    socket = amqp_tcp_socket_new ( conn );
    if ( !socket )
    {
        die ( "creating TCP socket" );
    }

    status = amqp_socket_open ( socket, hostname, port );
    if ( status )
    {
        die ( "opening TCP socket" );
    }

    die_on_amqp_error ( amqp_login ( conn, "/", 0, 131072, 0, AMQP_SASL_METHOD_PLAIN, "guest", "guest" ),
                        "Logging in" );
    amqp_channel_open ( conn, 1 );
    die_on_amqp_error ( amqp_get_rpc_reply ( conn ), "Opening channel" );

    send_batch ( conn, "test queue", rate_limit, message_count );

    die_on_amqp_error ( amqp_channel_close ( conn, 1, AMQP_REPLY_SUCCESS ), "Closing channel" );
    die_on_amqp_error ( amqp_connection_close ( conn, AMQP_REPLY_SUCCESS ), "Closing connection" );
    die_on_error ( amqp_destroy_connection ( conn ), "Ending connection" );

    return 0;
}
