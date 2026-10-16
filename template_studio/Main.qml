import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ApplicationWindow {
    id: window
    visible: true
    width: 1480; height: 900; minimumWidth: 1120; minimumHeight: 700
    title: "Beta Render · Thư viện hiệu ứng"
    color: "#0b141b"
    property color panel: "#14242f"
    property color border: "#294451"
    property color mint: "#72edcb"
    property color muted: "#9aabb6"
    property int activeTab: startInLibrary ? 2 : 0
    property string librarySearch: ""
    property string libraryCategory: "Tất cả"
    property var libraryItems: studio.library.filter(function(item) {
        return (libraryCategory === "Tất cả" || item.category === libraryCategory)
            && (item.name + " " + item.id).toLowerCase().indexOf(librarySearch.toLowerCase()) >= 0
    })
    property var candidate: studio.library.find(function(item) { return item.id === studio.candidateEffect }) || null
    property var current: studio.currentIndex >= 0 && studio.currentIndex < studio.rows.length ? studio.rows[studio.currentIndex] : null

    function setOption(key, value) { studio.configure(key, value) }
    function changeOffset(delta) { studio.preview(Math.max(0, delta)) }

    Shortcut { sequence: "Ctrl+O"; onActivated: studio.importFiles() }
    Shortcut { sequence: "Ctrl+Shift+O"; onActivated: studio.importFolder() }
    Shortcut { sequence: "F5"; onActivated: studio.preview(0) }
    Shortcut { sequence: "Ctrl+Enter"; onActivated: studio.runBatch() }
    Shortcut { sequence: "Escape"; onActivated: studio.stop() }
    Shortcut { sequence: "Delete"; onActivated: studio.remove() }
    onClosing: function(close) { close.accepted = studio.requestClose() }
    Connections { target: studio; function onCloseReady() { Qt.quit() } }
    Dialog {
        id: updateDialog; title: "Cài bản cập nhật"; modal: true; anchors.centerIn: parent
        standardButtons: Dialog.Ok | Dialog.Cancel
        Label { text: "App sẽ tải, xác minh và khởi động lại.\nCấu hình và video xuất được giữ nguyên."; color: "#dce6eb" }
        onAccepted: studio.installUpdate()
    }
    footer: Rectangle {
        height: 42; color: "#10212b"
        RowLayout { anchors.fill: parent; anchors.leftMargin: 18; anchors.rightMargin: 18; spacing: 10
            Label { text: "v" + studio.version; color: mint }
            Label { text: studio.updateNotice; color: muted; elide: Text.ElideRight; Layout.fillWidth: true }
            Button { text: "Chuẩn bị FFmpeg"; visible: !studio.mediaReady; enabled: !studio.busy; onClicked: studio.prepareMedia() }
            Button { text: "Kiểm tra cập nhật"; enabled: !studio.busy; onClicked: studio.checkUpdates() }
            Button { text: "Cài và khởi động lại"; visible: studio.updateAvailable; enabled: !studio.busy; onClicked: updateDialog.open() }
        }
    }

    header: Rectangle {
        height: 58; color: "#10212b"; border.color: border
        RowLayout { anchors.fill: parent; anchors.leftMargin: 20; anchors.rightMargin: 20; spacing: 20
            RowLayout { spacing: 10
                Image { objectName: "appLogo"; source: "assets/beta-render.png"; Layout.preferredWidth: 36; Layout.preferredHeight: 36; fillMode: Image.PreserveAspectFit; mipmap: true; Accessible.name: "Logo Beta Render" }
                Label { text: "Beta Render"; color: mint; font.pixelSize: 19; font.bold: true }
            }
            Label { text: "Trong như pha lê · 9:16"; color: "#dce6eb"; font.pixelSize: 14 }
            Item { Layout.fillWidth: true }
            Label { text: studio.hardware; color: muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.maximumWidth: 220 }
            Label { text: "LOCAL"; color: mint; font.bold: true }
            TabBar {
                id: tabs
                currentIndex: window.activeTab
                onCurrentIndexChanged: window.activeTab = currentIndex
                TabButton { text: "Xử lý hàng loạt" }
                TabButton { text: "Preview hiệu ứng" }
                TabButton { text: "Thư viện filter"; onClicked: studio.refreshLibrary() }
            }
        }
    }

    DropArea { anchors.fill: parent; keys: ["text/uri-list"]
        onDropped: function(drop) { if (drop.urls.length) studio.dropFiles(drop.urls) }
    }
    StackLayout { id: pages; anchors.fill: parent; anchors.margins: 14; currentIndex: window.activeTab
        Item {
            RowLayout { anchors.fill: parent; spacing: 12
            Rectangle { Layout.preferredWidth: 360; Layout.fillHeight: true; color: panel; border.color: border; radius: 8
            ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 10
                RowLayout { Layout.fillWidth: true
                    Label { text: "01  NGUỒN VIDEO"; color: mint; font.bold: true; Layout.fillWidth: true }
                    Label { text: studio.rows.length + "/200"; color: muted }
                }
                RowLayout { Layout.fillWidth: true
                    Button { text: "+ Video"; onClicked: studio.importFiles(); Layout.fillWidth: true }
                    Button { text: "+ Thư mục"; onClicked: studio.importFolder(); Layout.fillWidth: true }
                }
                Label { text: "Kéo thả video vào cửa sổ · chạy tuần tự"; color: muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                ListView { id: list; Layout.fillWidth: true; Layout.fillHeight: true; clip: true; model: studio.rows; spacing: 5
                    delegate: Rectangle { width: list.width; height: 62; radius: 6; color: index === studio.currentIndex ? "#1d4149" : "#192c37"; border.color: index === studio.currentIndex ? mint : border
                        MouseArea { anchors.fill: parent; onClicked: studio.select(index) }
                        Column { anchors.left: parent.left; anchors.leftMargin: 10; anchors.verticalCenter: parent.verticalCenter; width: parent.width-80; spacing: 4
                            Label { text: modelData.name; color: "#e5edf1"; elide: Text.ElideMiddle; width: parent.width }
                            Label { text: modelData.status + (modelData.detail ? " · "+modelData.detail : ""); color: modelData.status === "Lỗi" ? "#ff9da9" : muted; font.pixelSize: 11; elide: Text.ElideRight; width: parent.width }
                        }
                        Label { anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter; text: modelData.percent+"%"; color: mint; font.pixelSize: 11 }
                    }
                }
                RowLayout { Layout.fillWidth: true
                    Button { text: "Xóa chọn"; enabled: studio.currentIndex >= 0 && !studio.busy; onClicked: studio.remove(); Layout.fillWidth: true }
                    Button { text: "Xóa hết"; enabled: studio.rows.length > 0 && !studio.busy; onClicked: studio.clear(); Layout.fillWidth: true }
                }
            }
        }
        ColumnLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#101b23"; border.color: border; radius: 8
                ColumnLayout { anchors.fill: parent; anchors.margins: 14
                    Label { text: "02  PREVIEW TEMPLATE"; color: mint; font.bold: true }
                    Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d11"; radius: 6
                        Video { id: player; anchors.centerIn: parent; width: Math.min(parent.width*.48, 360); height: width*16/9; fillMode: VideoOutput.PreserveAspectFit; source: studio.previewUrl; visible: studio.previewUrl !== ""; autoPlay: true; loops: MediaPlayer.Infinite }
                        Label { anchors.centerIn: parent; visible: !player.visible; text: studio.currentIndex < 0 ? "Thêm video để xem preview" : "Bấm F5 hoặc Preview"; color: muted; font.pixelSize: 15 }
                    }
                    RowLayout { Layout.fillWidth: true
                        Button { text: "▶  Preview 8 giây"; enabled: !studio.busy && studio.currentIndex >= 0; onClicked: studio.preview(0); Layout.fillWidth: true }
                        Label { text: studio.notice; color: muted; elide: Text.ElideRight; Layout.fillWidth: true }
                    }
                }
            }
            Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 330; color: panel; border.color: border; radius: 8
                GridLayout { anchors.fill: parent; anchors.margins: 14; columns: 4; rowSpacing: 9; columnSpacing: 10
                    Label { text: "03  CẤU HÌNH CHUNG"; color: mint; font.bold: true; Layout.columnSpan: 4 }
                    Label { text: "Khung"; color: muted }
                    Label { text: "9:16 dọc · 1080p"; color: "#e5edf1"; Layout.columnSpan: 3 }
                    Label { text: "Clip chính"; color: muted }
                    Slider { from: 30; to: 100; value: studio.settings.scale; onMoved: setOption("scale", value); Layout.columnSpan: 2 }
                    Label { text: Math.round(studio.settings.scale)+"%"; color: mint }
                    Label { text: "Nền mờ"; color: muted }
                    Slider { from: 0; to: 60; value: studio.settings.blur; onMoved: setOption("blur", value); Layout.columnSpan: 2 }
                    Label { text: Math.round(studio.settings.blur)+" px"; color: mint }
                    Label { text: "Hiệu ứng mở đầu"; color: muted }
                    Slider { from: 0; to: 8; value: studio.settings.intro; onMoved: setOption("intro", value); Layout.columnSpan: 2 }
                    Label { text: studio.settings.intro.toFixed(1)+" giây"; color: mint }
                    Label { text: "Cường độ pha lê"; color: muted }
                    Slider { from: 0; to: 100; value: studio.settings.strength; onMoved: setOption("strength", value); Layout.columnSpan: 2 }
                    Label { text: Math.round(studio.settings.strength)+"%"; color: mint }
                    Label { text: "Tốc độ"; color: muted }
                    ComboBox { model: [0.5,0.75,1.0,1.25,1.5,2.0]; currentIndex: model.indexOf(studio.settings.speed); onActivated: setOption("speed", Number(currentText)); Layout.columnSpan: 3 }
                    Label { text: "Filter đang dùng"; color: muted }
                    Label { text: studio.effectName; color: mint; elide: Text.ElideRight; Layout.columnSpan: 2; Layout.fillWidth: true }
                    Button { text: "Chọn"; enabled: !studio.busy; onClicked: { window.activeTab = 2; studio.refreshLibrary() } }
                    Label { text: "Cường độ filter"; color: muted }
                    Slider { from: 0; to: 100; value: studio.settings.effectIntensity; enabled: !studio.busy; onMoved: setOption("effectIntensity", value); Layout.columnSpan: 2 }
                    Label { text: Math.round(studio.settings.effectIntensity) + "%"; color: mint }
}
            }
        }
        Rectangle { Layout.preferredWidth: 300; Layout.fillHeight: true; color: panel; border.color: border; radius: 8
            ColumnLayout { anchors.fill: parent; anchors.margins: 14; spacing: 10
                Label { text: "04  XUẤT HÀNG LOẠT"; color: mint; font.bold: true }
                Label { text: "Mỗi video một file · nguồn giữ nguyên"; color: muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label { text: "Thư mục xuất"; color: muted }
                TextField { text: studio.output; readOnly: true; Layout.fillWidth: true }
                Button { text: "Chọn thư mục"; onClicked: studio.chooseOutput(); Layout.fillWidth: true }
                Button { text: "Mở thư mục"; onClicked: studio.openOutput(); Layout.fillWidth: true }
                Item { Layout.fillHeight: true }
                Rectangle { Layout.fillWidth: true; height: 1; color: border }
                Label { text: "Phím tắt"; color: mint; font.bold: true }
                Label { text: "Ctrl+O  thêm video\nF5  tạo preview\nCtrl+Enter  bắt đầu xuất\nEsc  dừng an toàn\nDelete  bỏ video chọn"; color: muted; lineHeight: 1.25; Layout.fillWidth: true }
                Button {
                    text: studio.busy ? "■  Dừng tác vụ" : "▶  XUẤT TẤT CẢ"
                    enabled: studio.busy || studio.rows.length > 0
                    onClicked: studio.busy ? studio.stop() : studio.runBatch()
                    Layout.fillWidth: true; height: 44
                    background: Rectangle { color: studio.busy ? "#71394a" : mint; radius: 6 }
                    contentItem: Label { text: parent.text; color: studio.busy ? "#fff" : "#082019"; font.bold: true; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
            }
            }
            }
        }
        Item {
            Rectangle { anchors.fill: parent; color: "#101b23"; border.color: border; radius: 8
                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 16
                    RowLayout { Layout.fillWidth: true
                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                            Label { text: "PREVIEW HIỆU ỨNG MỞ ĐẦU"; color: mint; font.pixelSize: 20; font.bold: true }
                            Label { text: studio.currentIndex < 0 ? "Chọn một video ở tab Xử lý hàng loạt để xem thử." : "Preview dùng đúng cấu hình hiện tại và render 8 giây đầu."; color: muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        }
                        Button { text: "↻  Tạo lại preview"; enabled: !studio.busy && studio.currentIndex >= 0; onClicked: studio.preview(0) }
                    }
                    RowLayout { Layout.fillWidth: true; Layout.fillHeight: true; spacing: 18
                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d11"; radius: 10; border.color: border
                            Video { id: effectPlayer; anchors.centerIn: parent; width: Math.min(parent.width * .55, 460); height: width * 16 / 9; fillMode: VideoOutput.PreserveAspectFit; source: studio.previewUrl; visible: studio.previewUrl !== ""; autoPlay: true; loops: MediaPlayer.Infinite }
                            Label { anchors.centerIn: parent; visible: !effectPlayer.visible; text: studio.currentIndex < 0 ? "Chưa có video để preview" : "Bấm Tạo lại preview hoặc phím F5"; color: muted; font.pixelSize: 16 }
                        }
                        Rectangle { Layout.preferredWidth: 300; Layout.fillHeight: true; color: panel; border.color: border; radius: 8
                            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 10
                                Label { text: "CẤU HÌNH ĐANG XEM"; color: mint; font.bold: true }
                                Label { text: "Hiệu ứng mở đầu"; color: muted }
                                Label { text: studio.settings.intro.toFixed(1) + " giây"; color: "#e5edf1"; font.pixelSize: 18 }
                                Label { text: "Cường độ pha lê"; color: muted }
                                Label { text: Math.round(studio.settings.strength) + "%"; color: "#e5edf1"; font.pixelSize: 18 }
                                Label { text: "Zoom clip"; color: muted }
                                Label { text: Math.round(studio.settings.scale) + "%"; color: "#e5edf1"; font.pixelSize: 18 }
                                Label { text: "Tốc độ"; color: muted }
                                Label { text: studio.settings.speed + "×"; color: "#e5edf1"; font.pixelSize: 18 }
                                Item { Layout.fillHeight: true }
                                Button { text: "Chỉnh cấu hình ở tab chính"; onClicked: { window.activeTab = 0; tabs.currentIndex = 0 } Layout.fillWidth: true }
                            }
                        }
                    }
                    Label { text: studio.notice; color: muted; elide: Text.ElideRight; Layout.fillWidth: true }
                }
            }
        }
        Item {
            RowLayout { anchors.fill: parent; spacing: 14
                Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: panel; radius: 8; border.color: border
                    ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 12
                        Label { text: "THƯ VIỆN FILTER / HIỆU ỨNG"; color: mint; font.bold: true; font.pixelSize: 19 }
                        Label { text: "Video-FX · 150 preset · 6 nhóm · " + studio.thumbnailSource; color: muted; Layout.fillWidth: true; elide: Text.ElideRight }
                        RowLayout { Layout.fillWidth: true
                            TextField { placeholderText: "Tìm filter: RGB, VHS, film, glow…"; Layout.fillWidth: true; onTextChanged: window.librarySearch = text }
                            ComboBox { model: ["Tất cả", "Glitch / kỹ thuật số", "VHS / băng cũ", "Màu điện ảnh", "Camera / ống kính", "Ánh sáng / hạt / thời tiết", "Nghệ thuật"]; onActivated: window.libraryCategory = currentText; Layout.preferredWidth: 230 }
                            Button { text: "Tạo thumbnail"; enabled: !studio.busy; onClicked: studio.refreshLibrary() }
                        }
                        GridView { id: effectGrid; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
                            cellWidth: Math.max(190, width / Math.max(1, Math.floor(width / 200))); cellHeight: 240
                            model: window.libraryItems; ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle { width: effectGrid.cellWidth - 10; height: 230; radius: 8
                                color: modelData.id === studio.candidateEffect ? "#1d4149" : "#192c37"
                                border.color: modelData.id === studio.candidateEffect ? mint : border
                                ColumnLayout { anchors.fill: parent; anchors.margins: 9; spacing: 6
                                    Image { source: modelData.thumbnail; Layout.fillWidth: true; Layout.fillHeight: true; fillMode: Image.PreserveAspectFit; asynchronous: true }
                                    Label { text: modelData.name; color: "#e5edf1"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: modelData.id === studio.settings.effect ? "✓ Đang áp dụng" : modelData.category; color: modelData.id === studio.settings.effect ? mint : muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                MouseArea { anchors.fill: parent; enabled: !studio.busy; cursorShape: Qt.PointingHandCursor
                                    onClicked: studio.inspectEffect(modelData.id)
                                    onDoubleClicked: studio.applyEffect()
                                }
                            }
                        }
                    }
                }
                Rectangle { Layout.preferredWidth: 330; Layout.fillHeight: true; color: "#101b23"; radius: 8; border.color: border
                    ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 12
                        Label { text: window.candidate ? window.candidate.name : "Chọn một filter"; color: mint; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Rectangle { Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d11"; radius: 6
                            Image { anchors.fill: parent; source: window.candidate ? window.candidate.thumbnail : ""; fillMode: Image.PreserveAspectFit; visible: !studio.libraryPreviewUrl }
                            Video { anchors.fill: parent; source: studio.libraryPreviewUrl; visible: studio.libraryPreviewUrl !== ""; fillMode: VideoOutput.PreserveAspectFit; autoPlay: true; loops: MediaPlayer.Infinite }
                        }
                        Label { text: "Cường độ " + Math.round(studio.candidateIntensity) + "%"; color: muted }
                        Slider { from: 0; to: 100; value: studio.candidateIntensity; enabled: !studio.busy; onMoved: studio.configureCandidate("effectIntensity", value); Layout.fillWidth: true }
                        Label { text: "Áp dụng trong"; color: muted }
                        ComboBox { model: ["Cả video", "3 giây đầu", "8 giây đầu", "30 giây đầu"]; property var durations: [0, 3, 8, 30]; currentIndex: Math.max(0, durations.indexOf(studio.candidateDuration)); enabled: !studio.busy; onActivated: studio.configureCandidate("effectDuration", durations[currentIndex]); Layout.fillWidth: true }
                        Button { text: "▶ Preview video 8 giây"; enabled: !studio.busy && studio.currentIndex >= 0; onClicked: studio.previewEffect(); Layout.fillWidth: true }
                        Button { text: "✓ Áp dụng vào cấu hình"; enabled: !studio.busy && window.candidate !== null; onClicked: studio.applyEffect(); Layout.fillWidth: true }
                        Label { text: "Preview dùng video đang chọn và cấu hình template. Thumbnail ở mức 65%. Video-FX xử lý frame trên CPU."; color: muted; font.pixelSize: 12; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Label { text: studio.notice; color: mint; wrapMode: Text.WordWrap; Layout.fillWidth: true; Layout.maximumHeight: 64; elide: Text.ElideRight }
                    }
                }
            }
        }
    }
}
