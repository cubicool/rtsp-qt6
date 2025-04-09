#include <QWidget>
#include <QImage>
#include <QTimer>
#include <QMutex>
#include <QPainter>
#include <QApplication>

#include <atomic>
#include <thread>

extern "C" {
	#include <libavcodec/avcodec.h>
	#include <libavformat/avformat.h>
	#include <libswscale/swscale.h>
	#include <libavutil/imgutils.h>
}

class FFmpegWidget: public QWidget {
Q_OBJECT

public:
	FFmpegWidget(const QString& url, QWidget* parent=nullptr):
	QWidget(parent),
	_url(url) {
		avformat_network_init();

		_thread = std::thread([this]() { decodingLoop(); });
	}

	~FFmpegWidget() {
		_running = false;

		if(_thread.joinable()) _thread.join();
		if(_codecCtx) avcodec_free_context(&_codecCtx);
		if(_fmtCtx) avformat_close_input(&_fmtCtx);
		if(_swsCtx) sws_freeContext(_swsCtx);
	}

protected:
	void paintEvent(QPaintEvent* event) override {
		QPainter painter(this);
		QMutexLocker locker(&_frameMutex);

		if(!_currentFrame.isNull()) painter.drawImage(rect(), _currentFrame);

		else painter.fillRect(rect(), Qt::black);
	}

private:
	// Too big to define HERE, we'll do it in its own thing below.
	void decodingLoop();

	QString _url;
	QImage _currentFrame;
	QMutex _frameMutex;

	std::thread _thread;
	std::atomic<bool> _running{true};

	AVFormatContext* _fmtCtx = nullptr;
	AVCodecContext* _codecCtx = nullptr;
	SwsContext* _swsCtx = nullptr;

	int videoStreamIndex = -1;
};

void FFmpegWidget::decodingLoop() {
	if(avformat_open_input(&_fmtCtx, _url.toUtf8().constData(), nullptr, nullptr) != 0) {
		qWarning("Failed to open stream");

		return;
	}

	if(avformat_find_stream_info(_fmtCtx, nullptr) < 0) {
		qWarning("Failed to find stream info");

		return;
	}

	videoStreamIndex = av_find_best_stream(_fmtCtx, AVMEDIA_TYPE_VIDEO, -1, -1, nullptr, 0);

	if(videoStreamIndex < 0) return;

	AVStream* stream = _fmtCtx->streams[videoStreamIndex];
	const AVCodec* decoder = avcodec_find_decoder(stream->codecpar->codec_id);

	if(!decoder) return;

	_codecCtx = avcodec_alloc_context3(decoder);

	avcodec_parameters_to_context(_codecCtx, stream->codecpar);
	avcodec_open2(_codecCtx, decoder, nullptr);

	_swsCtx = sws_getContext(
		_codecCtx->width,
		_codecCtx->height,
		_codecCtx->pix_fmt,
		_codecCtx->width,
		_codecCtx->height,
		AV_PIX_FMT_RGB24,
		SWS_BICUBIC,
		nullptr,
		nullptr,
		nullptr
	);

	AVPacket* packet = av_packet_alloc();
	AVFrame* frame = av_frame_alloc();
	AVFrame* rgbFrame = av_frame_alloc();
	int rgbSize = av_image_get_buffer_size(AV_PIX_FMT_RGB24, _codecCtx->width, _codecCtx->height, 1);

	std::vector<uint8_t> rgbBuffer(rgbSize);

	av_image_fill_arrays(
		rgbFrame->data,
		rgbFrame->linesize,
		rgbBuffer.data(),
		AV_PIX_FMT_RGB24,
		_codecCtx->width,
		_codecCtx->height,
		1
	);

	while(_running) {
		if(av_read_frame(_fmtCtx, packet) < 0) break;

		if(packet->stream_index == videoStreamIndex) {
			if(!avcodec_send_packet(_codecCtx, packet)) {
				while(!avcodec_receive_frame(_codecCtx, frame)) {
					sws_scale(
						_swsCtx,
						frame->data,
						frame->linesize,
						0,
						_codecCtx->height,
						rgbFrame->data,
						rgbFrame->linesize
					);

					QImage img(
						rgbFrame->data[0],
						_codecCtx->width,
						_codecCtx->height,
						rgbFrame->linesize[0],
						QImage::Format_RGB888
					);

					{
						QMutexLocker locker(&_frameMutex);

						_currentFrame = img.copy();
					}

					update();
				}
			}
		}

		av_packet_unref(packet);
	}

	av_frame_free(&frame);
	av_frame_free(&rgbFrame);
	av_packet_free(&packet);
}

int main(int argc, char** argv) {
	QApplication app(argc, argv);

	FFmpegWidget viewer("rtsp://localhost:8554/mystream");

	// viewer.setWindowTitle("rtsp-qt6-ffmpeg");
	viewer.resize(640, 480);
	viewer.show();

	return app.exec();
}

#include "rtsp-qt6-ffmpeg.moc"
