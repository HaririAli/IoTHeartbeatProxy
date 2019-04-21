"""
Developed By Ali Hariri <hariri.ali.93@gmail.com>
as part of the MSc. project at the University of Kent
"""
import socket
import time
import datetime
from threading import Thread
from argparse import ArgumentParser


elapsed = 0


# Logging messages used by the proxy channel
class Output:
    RECV_MSG = "Received {} bytes\n"
    SENT_MSG = "Sent {} bytes\n"
    FILTER_MSG = "\r\033[1;31m{} --> Filtering has started\033[0m\n"
    SOCKET_ERR = "Socket error!\n"
    CLIENT_CH_TAG = "\r{} --> Client-Channel: "
    SERVER_CH_TAG = "\r{} --> Server-Channel: "
    THREAD_EXIT = "Thread exited!\n"


# Proxy TCP channel. Used between the client and the proxy and between the server and the proxy.
class ProxyChannel(Thread, Output):

    def __init__(self, proxy, channel_socket, accepted_sizes, tag):
        super(ProxyChannel, self).__init__()
        self.forward = None  # forward is a reference to the send function of the other channel. Initially is none.
        self.proxy = proxy
        self.channel_socket = channel_socket
        self.tag = tag
        self.accepted_sizes = accepted_sizes
        if proxy.keep_alive:
            self.channel_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.channel_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, proxy.keep_interval)
            self.channel_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, proxy.keep_interval)
            self.channel_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 100)

    def read_data(self):
        data = self.channel_socket.recv(self.proxy.buffer_size)
        size = len(data)
        if self.proxy.verbose:
            print(self.tag.format(datetime.timedelta(seconds=elapsed)) + self.RECV_MSG.format(str(size)), end="")
        return data, size

    def send_data(self, data, size):
        self.channel_socket.sendall(data)
        if self.proxy.verbose:
            print(self.tag.format(datetime.timedelta(seconds=elapsed)) + self.SENT_MSG.format(str(size)), end="")

    def run(self):
        received_bytes = 1
        while received_bytes > 0 and self.proxy.running:
            try:
                data, received_bytes = self.read_data()
                # forward traffic only if filtering has not started or if the size of data is accepted to be forwarded.
                if not self.proxy.filtering or received_bytes in self.accepted_sizes:
                    self.forward(data, received_bytes)
            except socket.error as error:
                print(self.tag.format(datetime.timedelta(seconds=elapsed)) + self.SOCKET_ERR, end="")
                print(error)
                break
        print(self.tag.format(datetime.timedelta(seconds=elapsed)) + self.THREAD_EXIT, end="")


# Proxy class stores all configurations of the proxy, listens on a specific port and creates the TCP channels.
class Proxy(Output):

    def __init__(self, server_address, port, verbose, keep_alive, keep_interval, buffer_size, listen_address,
                 server_hb, client_hb):
        self.server_address = server_address
        self.port = port
        self.verbose = verbose
        self.keep_alive = keep_alive
        self.keep_interval = keep_interval
        self.buffer_size = buffer_size
        self.running = True
        self.filtering = False
        self.proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.proxy_socket.bind((listen_address, port))
        self.server_hb = server_hb
        self.client_hb = client_hb

    # listen for one connection and create 2 TCP channels when a client connects.
    def listen(self):
        self.proxy_socket.listen(1)
        client_ch_socket, _ = self.proxy_socket.accept()
        client_channel = ProxyChannel(self, client_ch_socket, self.client_hb, self.CLIENT_CH_TAG)
        server_ch_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_ch_socket.connect((self.server_address, self.port))
        server_channel = ProxyChannel(self, server_ch_socket, self.server_hb, self.SERVER_CH_TAG)
        client_channel.forward = server_channel.send_data
        server_channel.forward = client_channel.send_data
        client_channel.daemon = True
        server_channel.daemon = True
        client_channel.start()
        server_channel.start()

    def filter(self):
        self.filtering = True
        if self.verbose:
            print(self.FILTER_MSG.format(datetime.timedelta(seconds=elapsed)), end="")


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument("-p", "--port", dest="port", action="store", required=True, type=int,
                            help="server port number")
    arg_parser.add_argument("-t", "--filter-timer", dest="timer", action="store", required=True, type=int,
                            help="forwarding timer in seconds. The proxy starts filtering when timer expires")
    arg_parser.add_argument("-d", "--server-addr", dest="server", action="store", required=True, help="server address")
    arg_parser.add_argument("-b", "--buffer", dest="buffer_size", action="store", default=2048, type=int,
                            help="buffer size in bytes, default is 2048")
    arg_parser.add_argument("-l", "--listen-addr", dest="listen_address", action="store", default='0.0.0.0',
                            help="listen address, default is 0.0.0.0")
    arg_parser.add_argument("-k", "--keep-alive", action='store_true', default=False, dest="keep_alive",
                            help="Enable TCP-keepalive on sockets. Default is false")
    arg_parser.add_argument("-i", "--keep-interval", dest="keep_interval", action="store", default=5,
                            help="TCP-keepalive interval. Default is 5.")
    arg_parser.add_argument('-c', '--client-heartbeat', nargs='+', type=int, default=[], dest="client_hb",
                            action="store", help="Accepted heartbeat data sizes originating from the client (in bytes)")
    arg_parser.add_argument('-s', '--server-heartbeat', nargs='+', type=int, default=[], dest="server_hb",
                            action="store", help="Accepted heartbeat data sizes originating from the server (in bytes)")
    arg_parser.add_argument("-q", "--quite", action='store_false', default=True, dest="verbose",
                            help="quiet mode. Only timer and error will be displayed")
    args = arg_parser.parse_args()

    proxy = Proxy(args.server, args.port, args.verbose, args.keep_alive, args.keep_interval, args.buffer_size,
                  args.listen_address, args.server_hb, args.client_hb)
    proxy.listen()
    global elapsed
    while proxy.running:
        print("\r{}".format(datetime.timedelta(seconds=elapsed)), end="")
        elapsed += 1
        if elapsed == args.timer:
            proxy.filter()
        time.sleep(1)


if __name__ == "__main__":
    main()
