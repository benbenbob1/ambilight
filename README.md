# ambilight
TV Ambilight System using a Fadecandy board and a Raspberry Pi.

There are two main applications, one in Python and one in C++. The C++ one runs much smoother, but Python is useful for debugging new methods.

## Installation
To use, OpenCV and other Python or C++ requirements must be installed.

### Python
Run `sudo apt-get install python-opencv` to install OpenCV in Raspbian

Run `pip install -r requirements.txt` to install the rest of the python requirements

### C++ (Recommended)

#### Install required C++ dependencies
`sudo apt-get -y install build-essential cmake cmake-curses-gui pkg-config`

`sudo apt-get -y install libv4l-dev v4l-utils`

`sudo apt-get -y install libatlas-base-dev gfortran`

#### Download and install OpenCV 3
`mkdir ~/opencv && cd ~/opencv`

`git clone http://github.com/opencv/opencv`

`git clone http://github.com/opencv/opencv_contrib`

`cd opencv`

`mkdir build`

`cd build`

`cmake -D CMAKE_BUILD_TYPE=RELEASE \

	-D CMAKE_INSTALL_PREFIX=/usr/local \

	-D BUILD_WITH_DEBUG_INFO=OFF \

	-D BUILD_DOCS=OFF \

	-D BUILD_EXAMPLES=OFF \

	-D BUILD_TESTS=OFF \

	-D BUILD_opencv_ts=OFF \

	-D BUILD_PERF_TESTS=OFF \

	-D INSTALL_C_EXAMPLES=ON \

	-D INSTALL_PYTHON_EXAMPLES=ON \

	-D OPENCV_EXTRA_MODULES_PATH=../opencv_contrib/modules \

	-D ENABLE_NEON=ON \

	-D WITH_LIBV4L=ON \

        ../`

`sudo make` This will take a long time (~2hrs)

`sudo make install`

`sudo ldconfig`

#### Enable the camera
`sudo raspi-config` -> `Interfacing options`

#### Get application to run on startup
In order to get the C++ application (rpcVideo) to run on startup, we must add the startup script to the lxsession boot sequence:

`sudo nano /etc/xdg/lxsession/LXDE/autostart`

Add the following line to the end of the file:

`@/bin/sh /home/pi/ambilight/pirunonstartup.sh`
