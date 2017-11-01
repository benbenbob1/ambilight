g++ $(pkg-config --libs --cflags opencv) video.cpp -o video
g++ $(pkg-config --libs --cflags opencv) videoRPC.cpp -o rpcVideo