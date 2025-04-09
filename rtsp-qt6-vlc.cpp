#include <QApplication>
#include <QWidget>
#include <QImage>
#include <QPainter>
#include <QTimer>
#include <QMutex>

#include <vlc/vlc.h>

class VLCWidget: public QWidget {
Q_OBJECT

public:
	VLCWidget(const QString& rtspUrl, QWidget* parent=nullptr):
	QWidget(parent),
	_rtspUrl(rtspUrl) {
		setMinimumSize(640, 480);

		// Create VLC instance
		const char* const vlc_args[] = {
			"--no-audio",
			"--no-xlib",
		};

		_vlc = libvlc_new(sizeof(vlc_args) / sizeof(vlc_args[0]), vlc_args);

		// Create media player
		_media = libvlc_media_new_location(_vlc, _rtspUrl.toUtf8().constData());
		_mediaPlayer = libvlc_media_player_new_from_media(_media);

		// Create an initial QImage buffer
		_image = QImage(width(), height(), QImage::Format_RGB32);

		_image.fill(Qt::black);

		// Hook up raw frame callbacks
		libvlc_video_set_callbacks(
			_mediaPlayer,
			lockCallback,
			// (libvlc_video_unlock_cb)(unlockCallback),
			unlockCallback,
			displayCallback,
			this
		);

		libvlc_video_set_format(
			_mediaPlayer,
			"RV32",
			width(),
			height(),
			width() * 4
		);

		libvlc_media_player_play(_mediaPlayer);
	}

	~VLCWidget() {
		if(_mediaPlayer) {
			libvlc_media_player_stop(_mediaPlayer);
			libvlc_media_player_release(_mediaPlayer);
		}

		if(_media) libvlc_media_release(_media);

		if(_vlc) libvlc_release(_vlc);
	}

protected:
	void paintEvent(QPaintEvent*) override {
		QPainter painter(this);

		_frameMutex.lock();

		painter.drawImage(0, 0, _image);

		_frameMutex.unlock();
	}

private:
	QString _rtspUrl;
	QImage _image;
	QMutex _frameMutex;

	libvlc_instance_t* _vlc = nullptr;
	libvlc_media_t* _media = nullptr;
	libvlc_media_player_t* _mediaPlayer = nullptr;

	static void* lockCallback(void* opaque, void** planes) {
		auto* self = static_cast<VLCWidget*>(opaque);

		self->_frameMutex.lock();

		*planes = self->_image.bits();

		return nullptr;
	}

	static void unlockCallback(void* opaque, void*, void* const*) {
		auto* self = static_cast<VLCWidget*>(opaque);

		self->_frameMutex.unlock();
	}

	static void displayCallback(void* opaque, void*) {
		// auto* self = static_cast<VLCWidget*>(opaque);

		QMetaObject::invokeMethod(
			static_cast<VLCWidget*>(opaque),
			"update",
			Qt::QueuedConnection
		);
	}
};

int main(int argc, char* argv[]) {
	QApplication app(argc, argv);

	VLCWidget viewer("rtsp://localhost:8554/mystream");

	// viewer.setWindowTitle("rtsp-qt6-vlc");
	viewer.resize(640, 480);
	viewer.show();

	return app.exec();
}

#include "rtsp-qt6-vlc.moc"
