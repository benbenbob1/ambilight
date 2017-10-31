g++ $(pkg-config --cflags --libs opencv) -lraspicam -lraspicam_cv videoRPC.cpp -o rpcVideo
