cmake_minimum_required(VERSION 3.16)
project(rtsp-qt6)

# set(CMAKE_PREFIX_PATH "C:/Qt/6.8.2/msvc2022_64;D:/dev/local")
find_package(Qt6 REQUIRED COMPONENTS Widgets Multimedia MultimediaWidgets)
find_package(PkgConfig REQUIRED)

pkg_check_modules(VLC REQUIRED libvlc)
pkg_check_modules(AVFORMAT REQUIRED libavformat)
pkg_check_modules(AVCODEC REQUIRED libavcodec)
pkg_check_modules(AVUTIL REQUIRED libavutil)
pkg_check_modules(SWSCALE REQUIRED libswscale)

set(CMAKE_AUTOMOC ON)

# ---------------------------------------------------------------------- FFmpeg
add_executable(rtsp-qt6-qmediaplayer "rtsp-qt6-qmediaplayer.cpp")

target_compile_features(rtsp-qt6-qmediaplayer PUBLIC cxx_std_20)
target_link_libraries(rtsp-qt6-qmediaplayer PRIVATE
	Qt6::Core
	Qt6::Gui
	Qt6::Widgets
	Qt6::Multimedia
	Qt6::MultimediaWidgets
)

# ------------------------------------------------------------------------- VLC
add_executable(rtsp-qt6-vlc "rtsp-qt6-vlc.cpp")

target_compile_features(rtsp-qt6-vlc PUBLIC cxx_std_20)
target_link_libraries(rtsp-qt6-vlc PRIVATE
	Qt6::Core
	Qt6::Gui
	Qt6::Widgets
	${VLC_LIBRARIES}
)
target_include_directories(rtsp-qt6-vlc PRIVATE
	${VLC_INCLUDE_DIRS}
)

# ---------------------------------------------------------------------- FFmpeg
add_executable(rtsp-qt6-ffmpeg "rtsp-qt6-ffmpeg.cpp")

target_compile_features(rtsp-qt6-ffmpeg PUBLIC cxx_std_20)
target_link_libraries(rtsp-qt6-ffmpeg PRIVATE
	Qt6::Core
	Qt6::Gui
	Qt6::Widgets
	${AVFORMAT_LIBRARIES}
	${AVCODEC_LIBRARIES}
	${AVUTIL_LIBRARIES}
	${SWSCALE_LIBRARIES}
)
target_include_directories(rtsp-qt6-ffmpeg PRIVATE
	${AVFORMAT_INCLUDE_DIRS}
	${AVCODEC_INCLUDE_DIRS}
	${AVUTIL_INCLUDE_DIRS}
	${SWSCALE_INCLUDE_DIRS}
)
