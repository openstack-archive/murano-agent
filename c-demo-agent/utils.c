#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>

#include <stdint.h>
#include <amqp.h>
#include <amqp_framing.h>

#include "utils.h"

/* For usleep */
/* #define _BSD_SOURCE */

#include <stdint.h>

#include <sys/time.h>
#include <unistd.h>

uint64_t now_microseconds ( void )
{
    struct timeval tv;
    gettimeofday ( &tv, NULL );
    return ( uint64_t ) tv.tv_sec * 1000000 + ( uint64_t ) tv.tv_usec;
}

void microsleep ( int usec )
{
    usleep ( usec );
}

void die ( const char *fmt, ... )
{
    va_list ap;
    va_start ( ap, fmt );
    vfprintf ( stderr, fmt, ap );
    va_end ( ap );
    fprintf ( stderr, "\n" );
    exit ( 1 );
}

void die_on_error ( int x, char const *context )
{
    if ( x < 0 )
    {
        fprintf ( stderr, "%s: %s\n", context, amqp_error_string2 ( x ) );
        exit ( 1 );
    }
}

void die_on_amqp_error ( amqp_rpc_reply_t x, char const *context )
{
    switch ( x.reply_type )
    {
    case AMQP_RESPONSE_NORMAL:
        return;

    case AMQP_RESPONSE_NONE:
        fprintf ( stderr, "%s: missing RPC reply type!\n", context );
        break;

    case AMQP_RESPONSE_LIBRARY_EXCEPTION:
        fprintf ( stderr, "%s: %s\n", context, amqp_error_string2 ( x.library_error ) );
        break;

    case AMQP_RESPONSE_SERVER_EXCEPTION:
        switch ( x.reply.id )
        {
        case AMQP_CONNECTION_CLOSE_METHOD:
        {
            amqp_connection_close_t *m = ( amqp_connection_close_t * ) x.reply.decoded;
            fprintf ( stderr, "%s: server connection error %d, message: %.*s\n",
                      context,
                      m->reply_code,
                      ( int ) m->reply_text.len, ( char * ) m->reply_text.bytes );
            break;
        }
        case AMQP_CHANNEL_CLOSE_METHOD:
        {
            amqp_channel_close_t *m = ( amqp_channel_close_t * ) x.reply.decoded;
            fprintf ( stderr, "%s: server channel error %d, message: %.*s\n",
                      context,
                      m->reply_code,
                      ( int ) m->reply_text.len, ( char * ) m->reply_text.bytes );
            break;
        }
        default:
            fprintf ( stderr, "%s: unknown server error, method id 0x%08X\n", context, x.reply.id );
            break;
        }
        break;
    }

    exit ( 1 );
}

static void dump_row ( long count, int numinrow, int *chs )
{
    int i;

    printf ( "%08lX:", count - numinrow );

    if ( numinrow > 0 )
    {
        for ( i = 0; i < numinrow; i++ )
        {
            if ( i == 8 )
            {
                printf ( " :" );
            }
            printf ( " %02X", chs[i] );
        }
        for ( i = numinrow; i < 16; i++ )
        {
            if ( i == 8 )
            {
                printf ( " :" );
            }
            printf ( "   " );
        }
        printf ( "  " );
        for ( i = 0; i < numinrow; i++ )
        {
            if ( isprint ( chs[i] ) )
            {
                printf ( "%c", chs[i] );
            }
            else
            {
                printf ( "." );
            }
        }
    }
    printf ( "\n" );
}

static int rows_eq ( int *a, int *b )
{
    int i;

    for ( i=0; i<16; i++ )
        if ( a[i] != b[i] )
        {
            return 0;
        }

    return 1;
}

void amqp_dump ( void const *buffer, size_t len )
{
    unsigned char *buf = ( unsigned char * ) buffer;
    long count = 0;
    int numinrow = 0;
    int chs[16];
    int oldchs[16] = {0};
    int showed_dots = 0;
    size_t i;

    for ( i = 0; i < len; i++ )
    {
        int ch = buf[i];

        if ( numinrow == 16 )
        {
            int i;

            if ( rows_eq ( oldchs, chs ) )
            {
                if ( !showed_dots )
                {
                    showed_dots = 1;
                    printf ( "          .. .. .. .. .. .. .. .. : .. .. .. .. .. .. .. ..\n" );
                }
            }
            else
            {
                showed_dots = 0;
                dump_row ( count, numinrow, chs );
            }

            for ( i=0; i<16; i++ )
            {
                oldchs[i] = chs[i];
            }

            numinrow = 0;
        }

        count++;
        chs[numinrow++] = ch;
    }

    dump_row ( count, numinrow, chs );

    if ( numinrow != 0 )
    {
        printf ( "%08lX:\n", count );
    }
}
