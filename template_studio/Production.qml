import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ApplicationWindow {
    id: win
    visible: true
    width: 1440; height: 900; minimumWidth: 1100; minimumHeight: 720
    title: "Template Studio · Sản xuất video"
    color: "#0c1018"
    property var p: studio.production
    property color ink: "#edf2fc"
    property color muted: "#8f9cb3"
    property color accent: "#b9f46d"
    property var current: p.currentIndex >= 0 && p.currentIndex < p.rows.length ? p.rows[p.currentIndex] : null
    palette.window: "#141b28"; palette.windowText: ink; palette.text: ink
    palette.base: "#0e1420"; palette.button: "#263246"; palette.buttonText: ink
    palette.highlight: accent; palette.highlightedText: "#0c1710"
    font.family: "Segoe UI"
    font.pixelSize: 14

    component Action: Button {
        id: b
        property bool primary: false
        implicitHeight: 40; leftPadding: 16; rightPadding: 16
        contentItem: Text { text: b.text; color: b.primary ? "#15210b" : win.ink; font: b.font; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: b.enabled ? 1 : .4 }
        background: Rectangle { color: b.primary ? win.accent : (b.hovered ? "#2d3c52" : "#202b3d"); radius: 8; opacity: b.enabled ? 1 : .45 }
    }
    component Caption: Label { color: win.muted; font.pixelSize: 13 }
    component Section: Label { color: win.ink; font.bold: true; font.pixelSize: 16; topPadding: 4; bottomPadding: 4 }
    component SettingsCard: Pane {
        Layout.fillWidth: true; Layout.alignment: Qt.AlignTop; padding: 16
        background: Rectangle { color: "#1a2434"; radius: 10; border.color: "#2c3a50" }
    }
    Shortcut { sequence: "Ctrl+O"; onActivated: p.importFiles() }
    Shortcut { sequence: "Ctrl+Shift+O"; onActivated: p.importFolder() }
    Shortcut { sequence: "Ctrl+Return"; onActivated: p.runBatch() }
    Shortcut { sequence: "F5"; onActivated: p.preview(0) }
    Shortcut { sequence: "Escape"; onActivated: studio.stop() }
    onClosing: function(event) { event.accepted = studio.requestClose() }
    Connections { target: studio; function onCloseReady() { Qt.quit() } }
    DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.hasUrls) p.dropFiles(drop.urls) } }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 14
        RowLayout {
            Layout.fillWidth: true; spacing: 14
            Rectangle { width: 42; height: 42; radius: 12; color: accent
                Text { anchors.centerIn: parent; text: "✦"; font.pixelSize: 27; color: "#15210b" }
            }
            ColumnLayout { spacing: 1
                Label { text: "Template Studio"; color: ink; font.pixelSize: 23; font.bold: true }
                Caption { text: "Thả video vào. Chọn mẫu. Chạy." }
            }
            Item { Layout.fillWidth: true }
            Action { text: "Tài nguyên & cập nhật"; onClicked: settings.open() }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            Rectangle {
                objectName: "videoPanel"
                Layout.preferredWidth: 286; Layout.minimumWidth: 260; Layout.maximumWidth: 286
                Layout.fillHeight: true; radius: 14; color: "#151d2a"; border.color: "#263246"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Label { text: "Video của bạn"; color: ink; font.pixelSize: 18; font.bold: true }
                    RowLayout { Layout.fillWidth: true
                        Action { text: "+ Video"; Layout.fillWidth: true; enabled: !studio.busy; onClicked: p.importFiles() }
                        Action { text: "+ Thư mục"; Layout.fillWidth: true; enabled: !studio.busy; onClicked: p.importFolder() }
                    }
                    Item {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        ColumnLayout {
                            anchors.centerIn: parent; width: parent.width; spacing: 14; visible: p.rows.length === 0
                            Rectangle { Layout.alignment: Qt.AlignHCenter; width: 64; height: 64; radius: 18; color: "#223328"
                                Text { anchors.centerIn: parent; text: "+"; color: accent; font.pixelSize: 38; font.weight: Font.Light }
                            }
                            Label { text: "Kéo video hoặc\nthư mục vào đây"; color: ink; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Caption { text: "Tối đa 200 video\nNguồn được giữ nguyên"; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Action { text: "Chọn video"; primary: true; Layout.alignment: Qt.AlignHCenter; enabled: !studio.busy; onClicked: p.importFiles() }
                        }
                        ListView {
                            id: queue; anchors.fill: parent; model: p.rows; clip: true; spacing: 8
                            ScrollBar.vertical: ScrollBar {}
                            delegate: Rectangle {
                                required property var modelData
                                required property int index
                                width: queue.width; height: 126; radius: 10
                                color: index===p.currentIndex ? "#263449" : "#1a2434"
                                border.color: index===p.currentIndex ? "#52677c" : "#293448"
                                MouseArea { anchors.fill: parent; onClicked: p.select(index) }
                                ColumnLayout {
                                    anchors.fill: parent; anchors.margins: 10; spacing: 6
                                    RowLayout { Layout.fillWidth: true; spacing: 4
                                        CheckBox { checked: modelData.selected; enabled: !studio.busy; onClicked: p.toggle(index) }
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: modelData.name; color: ink; font.bold: true; font.pixelSize: 13; elide: Text.ElideMiddle; Layout.fillWidth: true }
                                            Caption { text: modelData.meta; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                            Caption { text: modelData.presetName; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Caption { text: modelData.detail===modelData.status ? "" : modelData.detail; font.pixelSize: 11; color: modelData.status==="Lỗi" || modelData.status==="Thiếu nguồn" ? "#ff9c9c" : muted; elide: Text.ElideRight; Layout.fillWidth: true
                                            ToolTip.visible: detailMouse.containsMouse; ToolTip.text: modelData.detail || modelData.status
                                            MouseArea { id: detailMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                                        }
                                        Label { text: modelData.status==="Đang xuất" ? modelData.percent+"%" : modelData.status; color: modelData.status==="Hoàn tất" ? accent : muted; font.pixelSize: 11; Layout.alignment: Qt.AlignRight }
                                    }
                                    ProgressBar { from: 0; to: 100; value: modelData.percent; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                    Caption { text: p.summary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Action { text: "Bỏ mục chọn"; Layout.fillWidth: true; enabled: !studio.busy && p.rows.length>0; onClicked: p.removeSelected() }
                    RowLayout { Layout.fillWidth: true; spacing: 8
                        Action { text: "Chạy lại lỗi"; Layout.fillWidth: true; leftPadding: 10; rightPadding: 10; font.pixelSize: 12; enabled: !studio.busy && p.rows.length>0; onClicked: p.retrySelected() }
                        Action { text: "Ẩn đã xong"; Layout.fillWidth: true; leftPadding: 10; rightPadding: 10; font.pixelSize: 12; enabled: !studio.busy; onClicked: p.clearDone() }
                    }
                }
            }
            Rectangle {
                objectName: "configurationPanel"
                Layout.fillWidth: true; Layout.minimumWidth: 420; Layout.fillHeight: true
                color: "#151d2a"; radius: 14; border.color: "#3c4e44"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                    Label { text: "Cấu hình preset"; color: ink; font.pixelSize: 20; font.bold: true }
                    ComboBox {
                        id: presets; Layout.fillWidth: true; implicitHeight: 44; enabled: !studio.busy
                        model: p.presets; textRole: "name"; valueRole: "id"
                        currentIndex: { for (var i=0;i<p.presets.length;i++) if(p.presets[i].id===p.presetId)return i; return 0 }
                        onActivated: p.choosePreset(currentValue)
                    }
                    Caption { text: "Áp dụng cho video chưa xuất · tự nhớ cấu hình"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ScrollView {
                        id: configurationScroll; objectName: "configurationScroll"
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                        ScrollBar.vertical.policy: ScrollBar.AlwaysOn
                        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                        ColumnLayout {
                            width: configurationScroll.availableWidth; spacing: 12
                            GridLayout {
                                objectName: "configurationGrid"
                                Layout.fillWidth: true; columns: width >= 620 ? 2 : 1; uniformCellWidths: true; columnSpacing: 12; rowSpacing: 12
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Xuất video" }
                                        Caption { text: "Chất lượng" }
                                        ComboBox { model: ["Tiết kiệm", "Tiêu chuẩn", "Chất lượng cao"]; property var ids: ["small","standard","high"]; currentIndex: ids.indexOf(p.config.quality); enabled: !studio.busy; onActivated: p.configure("quality",ids[currentIndex]); Layout.fillWidth: true }
                                        Caption { text: p.config.quality==="high" ? "CQ18 · dung lượng theo nội dung" : "Bitrate video (Mb/s)"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        TextField { text: String(p.config.video_bitrate); enabled: !studio.busy && p.config.quality!=="high"; validator: DoubleValidator { bottom: .5; top: 100; locale: "en_US" } onEditingFinished: p.configure("video_bitrate",Number(text)); Layout.fillWidth: true }
                                        Caption { text: "Bộ mã hóa" }
                                        ComboBox { model: ["Tự động · ưu tiên NVENC", "NVIDIA NVENC", "Mã hóa CPU"]; property var ids: ["auto","h264_nvenc","libx264"]; currentIndex: ids.indexOf(p.config.encoder); enabled: !studio.busy; onActivated: p.configure("encoder",ids[currentIndex]); Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true
                                            ComboBox { model: ["3:4","9:16"]; currentIndex: p.config.height/p.config.width>1.5 ? 1 : 0; enabled: !studio.busy; onActivated: p.configure("aspect",currentText); Layout.fillWidth: true }
                                            ComboBox { model: ["1080","720"]; currentIndex: p.config.width===1080 ? 0 : 1; enabled: !studio.busy; onActivated: p.configure("resolution",Number(currentText)); Layout.fillWidth: true }
                                        }
                                        CheckBox { text: "Tắt âm thanh"; checked: p.config.mute; enabled: !studio.busy; onClicked: p.configure("mute",checked) }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Hiệu ứng mở đầu" }
                                        CheckBox { text: "Ngũ giác mở đầu"; checked: p.config.intro_enabled; enabled: !studio.busy; onClicked: p.configure("intro_enabled",checked) }
                                        Caption { text: "Đoạn intro · " + (p.config.effect_end-p.config.effect_start).toFixed(2) + " giây" }
                                        Slider { from: 0; to: 8; value: p.config.effect_end; enabled: !studio.busy; onMoved: p.configure("effect_end",value); Layout.fillWidth: true }
                                        Caption { text: "Chuyển động · " + Math.round(p.config.effect_slider*100) + "%" }
                                        Slider { from: 0; to: 1; value: p.config.effect_slider; enabled: !studio.busy; onMoved: p.configure("effect_slider",value); Layout.fillWidth: true }
                                        Caption { text: "Khẩu độ · " + p.config.bokeh_size.toFixed(2) }
                                        Slider { from: 0; to: 1.5; value: p.config.bokeh_size; enabled: !studio.busy; onMoved: p.configure("bokeh_size",value); Layout.fillWidth: true }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Màu và nét" }
                                        CheckBox { text: "Bật màu và nét"; checked: p.config.filter_enabled; enabled: !studio.busy; onClicked: p.configure("filter_enabled",checked) }
                                        Caption { text: "Cường độ màu · " + Math.round(p.config.filter_intensity*100) + "%" }
                                        Slider { from: 0; to: 1; value: p.config.filter_intensity; enabled: !studio.busy; onMoved: p.configure("filter_intensity",value); Layout.fillWidth: true }
                                        Caption { text: "Độ nét · " + Math.round(p.config.sharpness*100) + "%" }
                                        Slider { from: 0; to: 1; value: p.config.sharpness; enabled: !studio.busy; onMoved: p.configure("sharpness",value); Layout.fillWidth: true }
                                        ComboBox { model: ["Màu thống nhất", "Ước lượng da · chroma"]; currentIndex: p.config.skin==="chroma" ? 1 : 0; enabled: !studio.busy; onActivated: p.configure("skin",currentIndex===1 ? "chroma" : "none"); Layout.fillWidth: true }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Bố cục và tốc độ" }
                                        Caption { text: "Scale clip · " + Math.round(p.config.scale*100) + "%" }
                                        Slider { from: .3; to: 1.5; value: p.config.scale; enabled: !studio.busy; onMoved: p.configure("scale",value); Layout.fillWidth: true }
                                        Caption { text: "Vị trí ngang / dọc" }
                                        Slider { from: -.3; to: .3; value: p.config.offset[0]; enabled: !studio.busy; onMoved: p.configure("offsetX",value); Layout.fillWidth: true }
                                        Slider { from: -.3; to: .3; value: p.config.offset[1]; enabled: !studio.busy; onMoved: p.configure("offsetY",value); Layout.fillWidth: true }
                                        Caption { text: "Nền mờ" }
                                        Slider { from: 0; to: .1; value: p.config.background_sigma_ratio; enabled: !studio.busy; onMoved: p.configure("background_sigma_ratio",value); Layout.fillWidth: true }
                                        CheckBox { text: "Lật ngang"; checked: p.config.flip; enabled: !studio.busy; onClicked: p.configure("flip",checked) }
                                        Caption { text: "Tốc độ video (×)" }
                                        TextField { text: String(p.config.playback_rate); validator: DoubleValidator { bottom: .5; top: 2; locale: "en_US" } enabled: !studio.busy; onEditingFinished: p.configure("playback_rate",Number(text)); Layout.fillWidth: true }
                                    }
                                }
                            }
                            SettingsCard {
                                objectName: "customPresetCard"
                                contentItem: ColumnLayout { spacing: 8
                                    Section { text: "Preset của bạn" }
                                    RowLayout { Layout.fillWidth: true
                                        TextField { id: presetName; placeholderText: "Tên preset của bạn"; Layout.fillWidth: true }
                                        Action { text: "Lưu mẫu"; enabled: !studio.busy && presetName.text.trim()!==""; onClicked: { p.savePreset(presetName.text);presetName.clear() } }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Action { text: "Nhập preset"; enabled: !studio.busy; onClicked: p.importPreset(); Layout.fillWidth: true }
                                        Action { text: "Xuất preset"; enabled: !studio.busy; onClicked: p.exportPreset(); Layout.fillWidth: true }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            Rectangle {
                objectName: "previewPanel"
                Layout.preferredWidth: 312; Layout.minimumWidth: 270; Layout.maximumWidth: 350
                Layout.fillHeight: true; color: "#151d2a"; radius: 14; border.color: "#263246"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout { Layout.fillWidth: true
                        Label { text: "Xem thử"; color: ink; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true }
                        CheckBox { text: "Nguồn"; checked: p.sourceMode; onClicked: p.showSource(checked) }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d15"; radius: 10; clip: true
                        Video { id: previewPlayer; anchors.fill: parent; source: p.previewUrl; fillMode: VideoOutput.PreserveAspectFit; autoPlay: true; loops: MediaPlayer.Infinite; visible: p.previewUrl!=="" }
                        Column { anchors.centerIn: parent; width: parent.width-32; spacing: 12; visible: !previewPlayer.visible
                            Text { text: "✦"; color: "#536881"; font.pixelSize: 48; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                            Text { text: current ? "Chọn Preview để xem hiệu ứng" : "Chọn một video để xem thử"; color: muted; width: parent.width; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                        }
                        Rectangle { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 34; color: "#be563e"; visible: p.previewStale
                            Text { anchors.centerIn: parent; text: "Cấu hình đã đổi · tạo lại preview"; color: "white"; font.pixelSize: 11 }
                        }
                    }
                    Slider { from: 0; to: Math.max(1,previewPlayer.duration); value: previewPlayer.position; onMoved: previewPlayer.seek(value); Layout.fillWidth: true; enabled: p.previewUrl!=="" }
                    RowLayout { Layout.fillWidth: true
                        Action { text: previewPlayer.playbackState===MediaPlayer.PlayingState ? "Dừng hình" : "Phát"; enabled: p.previewUrl!==""; onClicked: previewPlayer.playbackState===MediaPlayer.PlayingState ? previewPlayer.pause() : previewPlayer.play() }
                        Action { text: "Preview 3 giây"; Layout.fillWidth: true; enabled: !studio.busy && p.ready && p.currentIndex>=0; onClicked: p.preview(0) }
                    }
                    RowLayout { Layout.fillWidth: true
                        Caption { text: "Từ giây" }
                        SpinBox { id: offset; from: 0; to: current ? Math.max(0,Math.floor(current.duration/p.config.playback_rate)-3) : 0; editable: true; Layout.fillWidth: true }
                        Action { text: "Xem đoạn"; enabled: !studio.busy && p.ready && p.currentIndex>=0; onClicked: p.preview(offset.value) }
                    }
                    Action { text: "Mở file kết quả"; Layout.fillWidth: true; enabled: current!==null && !!current.result; onClicked: p.openResult() }
                }
            }
        }

        Rectangle {
            Layout.fillWidth: true; implicitHeight: 128; radius: 14; color: "#17221c"; border.color: "#344734"
            ColumnLayout { anchors.fill: parent; anchors.margins: 16; spacing: 10
                RowLayout { Layout.fillWidth: true
                    Caption { text: "Lưu vào" }
                    Label { text: p.output; color: ink; elide: Text.ElideMiddle; Layout.fillWidth: true }
                    Action { text: "Đổi"; enabled: !studio.busy; onClicked: p.chooseOutput() }
                    Action { text: "Mở thư mục"; onClicked: p.openOutput() }
                }
                RowLayout { Layout.fillWidth: true; spacing: 16
                    ColumnLayout { Layout.fillWidth: true; spacing: 7
                        Label { text: studio.busy ? studio.notice : (!p.ready ? p.runtimeNotice : studio.notice); color: p.ready ? ink : "#e6c481"; elide: Text.ElideRight; Layout.fillWidth: true }
                        ProgressBar { from: 0; to: 100; value: p.overall; Layout.fillWidth: true }
                        Caption { text: p.estimate }
                    }
                    Action { text: "Xong file thì dừng"; visible: p.batchRunning; onClicked: p.stopAfterFile() }
                    Action { text: studio.busy ? "Dừng ngay" : "▶  Chạy"; primary: !studio.busy; implicitWidth: 145; implicitHeight: 48
                        enabled: studio.busy || (p.ready && p.rows.length>0)
                        onClicked: studio.busy ? studio.stop() : p.runBatch()
                    }
                }
            }
        }
    }

    Drawer {
        id: settings; edge: Qt.RightEdge; width: Math.min(660, win.width-80); height: win.height
        background: Rectangle { color: "#151d2a" }
        ScrollView { anchors.fill: parent; clip: true; contentWidth: availableWidth
            ColumnLayout { width: settings.width-42; x: 20; spacing: 8
                RowLayout { Layout.fillWidth: true
                    Label { text: "Tài nguyên & cập nhật"; color: ink; font.pixelSize: 23; font.bold: true; Layout.fillWidth: true; topPadding: 20 }
                    Action { text: "Đóng"; onClicked: settings.close() }
                }
                Section { text: "Tài nguyên và GPU" }
                Caption { text: p.runtimeNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Caption { text: "Cache effect được giữ local, nhập một lần trên máy này."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true
                    Action { text: "Nhập RAR"; enabled: !studio.busy; onClicked: p.importAssets(); Layout.fillWidth: true }
                    Action { text: "Chọn thư mục cache"; enabled: !studio.busy; onClicked: p.importAssetsFolder(); Layout.fillWidth: true }
                }
                Action { text: "Kiểm tra GPU"; enabled: !studio.busy; onClicked: p.checkRuntime(); Layout.fillWidth: true }
                Action { text: "Chuẩn bị FFmpeg"; visible: !studio.mediaReady; enabled: !studio.busy; onClicked: studio.prepareMedia(); Layout.fillWidth: true }
                Section { text: "Ứng dụng · v" + studio.version }
                Caption { text: studio.updateNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Action { text: "Kiểm tra cập nhật"; enabled: !studio.busy; onClicked: studio.checkUpdates(); Layout.fillWidth: true }
                Action { text: "Cài và khởi động lại"; visible: studio.updateAvailable; enabled: !studio.busy; primary: true; onClicked: studio.installUpdate(); Layout.fillWidth: true }
                Action { text: "Mở nhật ký"; onClicked: p.openLogs(); Layout.fillWidth: true }
                Item { height: 20 }
            }
        }
    }
}
