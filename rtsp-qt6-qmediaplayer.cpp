#include <QApplication>
#include <QMediaPlayer>
#include <QMediaMetaData>
#include <QVideoWidget>
#include <QUrl>

#include <iostream>

int main(int argc, char** argv) {
	QApplication app(argc, argv);

	QMediaPlayer player;

	QObject::connect(&player, &QMediaPlayer::mediaStatusChanged, [](QMediaPlayer::MediaStatus status) {
		qDebug() << "Media status changed:" << status;
	});

	QObject::connect(&player, &QMediaPlayer::positionChanged, [](qint64 pos) {
		qDebug() << "Position changed:" << pos;
	});

	QObject::connect(&player, &QMediaPlayer::metaDataChanged, [&player]() {
		qDebug() << "Metadata changed:";

		for(const auto& key : player.metaData().keys()) {
			qDebug() << key << ":" << player.metaData().stringValue(key);
		}
	});

	QVideoWidget videoWidget;

	player.setVideoOutput(&videoWidget);

	videoWidget.show();

	const QUrl url = QUrl("rtsp://127.0.0.1:8554/test");

	player.setSource(url);
	player.play();

	return QApplication::exec();
}
