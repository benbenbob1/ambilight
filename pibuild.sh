g++ $(pkg-config --cflags --libs opencv) -L /opt/vc/lib -lraspicam -lraspicam_cv -lmmal -lmmal_core -lmmal_util video.cpp -o video
