#include <QApplication>
#include <QMediaPlayer>
#include <QVideoSink>
#include <QVideoFrame>
#include <QImage>
#include <QWidget>
#include <QPainter>
#include <QLabel>
#include <QVBoxLayout>
#include <QUrl>

class VideoWidget : public QWidget {
    Q_OBJECT
public:
    explicit VideoWidget(QWidget *parent = nullptr)
        : QWidget(parent)
    {
        setMinimumSize(640, 480);
        setAttribute(Qt::WA_OpaquePaintEvent);
        setAttribute(Qt::WA_NoSystemBackground);
    }

    void setFrame(const QImage &frame) {
        m_frame = frame;
        update();
    }

protected:
    void paintEvent(QPaintEvent *) override {
        QPainter p(this);
        if (!m_frame.isNull())
            p.drawImage(rect(), m_frame);
        // No need to draw overlays here; QLabel handles that.
    }

private:
    QImage m_frame;
};

class MainWindow : public QWidget {
    Q_OBJECT
public:
    MainWindow(QWidget *parent = nullptr)
        : QWidget(parent)
    {
        auto *layout = new QVBoxLayout(this);
        layout->setContentsMargins(0, 0, 0, 0);

        videoWidget = new VideoWidget(this);
        layout->addWidget(videoWidget);

        overlayLabel = new QLabel("Overlay Text", videoWidget);
        overlayLabel->move(20, 20);
        overlayLabel->setStyleSheet("QLabel { font-size: 40px; color: white; background-color: rgba(0, 0, 0, 128); padding: 4px; }");

        sink = new QVideoSink(this);
        connect(sink, &QVideoSink::videoFrameChanged, this, [this](const QVideoFrame &frame) {
            if (frame.isValid())
                videoWidget->setFrame(frame.toImage());
        });

        player = new QMediaPlayer(this);
        player->setVideoOutput(sink);

        // Replace with a working RTSP stream or file path
        player->setSource(QUrl("rtsp://127.0.0.1:8554/test"));
        player->play();
    }

private:
    VideoWidget *videoWidget;
    QLabel *overlayLabel;
    QMediaPlayer *player;
    QVideoSink *sink;
};

int main(int argc, char *argv[])
{
    QApplication a(argc, argv);
    MainWindow w;
    w.show();
    return a.exec();
}

#include "rtsp-qt6-qvideosink.moc"
