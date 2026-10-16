import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ApplicationWindow {
    id: win
    visible: true
    width: 1440; height: 900; minimumWidth: 1100; minimumHeight: 720
    title: "Template Studio"
    color: "#0c1018"
    property var p: studio.production
    property color ink: "#edf2fc"
    property color muted: "#a0adc1"
    property color accent: "#b9f46d"
    property var current: p.currentIndex >= 0 && p.currentIndex < p.rows.length ? p.rows[p.currentIndex] : null
    palette.window: "#141b28"; palette.windowText: ink; palette.text: ink
    palette.base: "#0e1420"; palette.button: "#263246"; palette.buttonText: ink
    palette.highlight: accent; palette.highlightedText: "#0c1710"
    font.family: "Segoe UI"
    font.pixelSize: 14

    function statusText(status) {
        return ({"Chờ xử lý": "Chờ xuất", "Hoàn tất": "Đã xuất", "Thiếu nguồn": "Mất file nguồn"})[status] || status
    }
    function timeText(milliseconds) {
        var seconds = Math.floor(milliseconds/1000)
        return Math.floor(seconds/60) + ":" + (seconds%60 < 10 ? "0" : "") + seconds%60
    }

    component Action: Button {
        id: b
        property bool primary: false
        property bool danger: false
        implicitHeight: 38; leftPadding: 12; rightPadding: 12; font.pixelSize: 13
        contentItem: Text { text: b.text; color: b.primary ? "#15210b" : (b.danger ? "#ffb9bd" : win.ink); font: b.font; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: b.enabled ? 1 : .5 }
        background: Rectangle { color: b.primary ? (b.down ? "#a4da5d" : win.accent) : (b.danger ? "#482a31" : (b.down ? "#33445b" : b.hovered ? "#2c3b50" : "#202c3e")); border.color: b.visualFocus ? win.accent : (b.primary ? "transparent" : "#35455b"); radius: 6; opacity: b.enabled ? 1 : .5 }
    }
    component Select: ComboBox {
        id: select
        implicitHeight: 38; leftPadding: 12; rightPadding: 32; font.pixelSize: 13
        contentItem: Text { objectName: select.objectName+"Text"; text: select.displayText; font: select.font; color: select.enabled ? win.ink : "#8290a5"; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        background: Rectangle { color: "#101824"; border.color: select.visualFocus || select.popup.visible ? win.accent : (select.hovered ? "#63758e" : "#42526a"); radius: 6; opacity: select.enabled ? 1 : .5 }
        indicator: Canvas {
            x: select.width-width-12; y: (select.height-height)/2; width: 10; height: 6; opacity: select.enabled ? 1 : .4
            onPaint: { var c=getContext("2d"); c.clearRect(0,0,width,height); c.strokeStyle="#b9c6d8"; c.lineWidth=1.6; c.beginPath(); c.moveTo(1,1); c.lineTo(5,5); c.lineTo(9,1); c.stroke() }
        }
        delegate: ItemDelegate {
            id: option
            required property var modelData
            required property int index
            property bool selected: select.currentIndex===index
            width: select.popup.availableWidth; height: 38; leftPadding: 10; rightPadding: 10
            highlighted: select.highlightedIndex===index
            contentItem: Text {
                objectName: "optionText"
                text: select.textRole ? option.modelData[select.textRole] : option.modelData
                color: option.selected ? "#15210b" : "#edf2fc"
                font.pixelSize: 13; font.weight: option.selected ? Font.DemiBold : Font.Normal
                verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight
            }
            background: Rectangle { color: option.selected ? win.accent : (option.hovered || option.highlighted ? "#33455f" : "transparent"); radius: 4 }
        }
        popup: Popup {
            objectName: select.objectName+"Popup"
            y: select.height+5; width: select.width; padding: 6
            implicitHeight: Math.min(contentItem.implicitHeight+12,320)
            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: select.popup.visible ? select.delegateModel : null; currentIndex: select.highlightedIndex; ScrollBar.vertical: Scroller {} }
            background: Rectangle { color: "#192333"; border.color: "#53647d"; radius: 8 }
        }
    }
    component Field: TextField {
        id: field
        implicitHeight: 38; leftPadding: 12; rightPadding: 12; font.pixelSize: 13
        color: enabled ? win.ink : "#8290a5"; placeholderTextColor: "#8c9bb0"
        selectByMouse: true; selectionColor: win.accent; selectedTextColor: "#15210b"
        background: Rectangle { color: "#101824"; radius: 6; border.color: field.activeFocus ? win.accent : "#42526a"; opacity: field.enabled ? 1 : .5 }
    }
    component Range: Slider {
        id: range
        implicitHeight: 28; padding: 4
        background: Rectangle {
            x: range.leftPadding; y: range.topPadding+(range.availableHeight-height)/2
            width: range.availableWidth; height: 4; radius: 2; color: "#405069"
            Rectangle { width: range.visualPosition*parent.width; height: parent.height; radius: 2; color: range.enabled ? "#a9ca88" : "#526078" }
        }
        handle: Rectangle {
            x: range.leftPadding+range.visualPosition*(range.availableWidth-width); y: range.topPadding+(range.availableHeight-height)/2
            implicitWidth: 16; implicitHeight: 16; radius: 8
            color: range.enabled ? (range.pressed ? win.accent : "#dbe6f3") : "#728097"
            border.color: range.visualFocus ? win.accent : "#53647c"; border.width: range.visualFocus ? 2 : 1
        }
    }
    component Check: CheckBox {
        id: check
        implicitHeight: 30; leftPadding: 2; rightPadding: 2; spacing: 8
        indicator: Rectangle {
            x: check.leftPadding; y: check.topPadding+(check.availableHeight-height)/2
            width: 18; height: 18; radius: 4; color: check.checked ? win.accent : "#101824"
            border.color: check.checked || check.visualFocus ? win.accent : (check.hovered ? "#91a3bd" : "#53647d")
            opacity: check.enabled ? 1 : .5
            Text { anchors.centerIn: parent; text: "✓"; color: "#15210b"; font.pixelSize: 14; font.bold: true; visible: check.checked }
        }
        contentItem: Text { text: check.text; font.pixelSize: 13; color: check.enabled ? win.ink : "#8290a5"; leftPadding: check.indicator.width+check.spacing; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
    }
    component NumberField: SpinBox {
        id: number
        implicitWidth: 84; implicitHeight: 38; leftPadding: 28; rightPadding: 28; font.pixelSize: 13
        editable: true
        contentItem: TextInput { text: number.textFromValue(number.value,number.locale); font: number.font; color: win.ink; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; readOnly: !number.editable; validator: number.validator; selectByMouse: true; selectionColor: win.accent; selectedTextColor: "#15210b"; inputMethodHints: Qt.ImhDigitsOnly }
        up.indicator: Rectangle { x: number.width-width; height: number.height; width: 28; color: number.up.pressed ? "#33455f" : "transparent"; radius: 6; Text { anchors.centerIn: parent; text: "+"; color: number.up.enabled ? win.ink : win.muted; font.pixelSize: 18 } }
        down.indicator: Rectangle { x: 0; height: number.height; width: 28; color: number.down.pressed ? "#33455f" : "transparent"; radius: 6; Text { anchors.centerIn: parent; text: "−"; color: number.down.enabled ? win.ink : win.muted; font.pixelSize: 18 } }
        background: Rectangle { color: "#101824"; border.color: number.activeFocus ? win.accent : "#42526a"; radius: 6 }
    }
    component Progress: ProgressBar {
        id: progress
        implicitHeight: 4
        background: Rectangle { color: "#2c3b51"; radius: 2 }
        contentItem: Item { Rectangle { width: progress.visualPosition*parent.width; height: parent.height; radius: 2; color: win.accent } }
    }
    component Scroller: ScrollBar {
        id: bar
        implicitWidth: 8; implicitHeight: 8; padding: 1; minimumSize: .12
        visible: policy===ScrollBar.AlwaysOn || (policy!==ScrollBar.AlwaysOff && size<1)
        background: Rectangle { color: "transparent" }
        contentItem: Rectangle { implicitWidth: 6; radius: 3; color: bar.pressed ? "#b9c6d8" : (bar.hovered ? "#8c9cb3" : "#52637d") }
    }
    component Caption: Label { color: win.muted; font.pixelSize: 13 }
    component Section: Label { color: win.ink; font.bold: true; font.pixelSize: 16; topPadding: 4; bottomPadding: 4 }
    component SettingsCard: Pane {
        Layout.fillWidth: true; Layout.fillHeight: true; padding: 16
        background: Rectangle { color: "#1a2434"; radius: 10; border.color: "#2c3a50" }
    }
    Shortcut { sequence: "Ctrl+O"; onActivated: p.importFiles() }
    Shortcut { sequence: "Ctrl+Shift+O"; onActivated: p.importFolder() }
    Shortcut { sequence: "Ctrl+Return"; onActivated: p.runBatch() }
    Shortcut { sequence: "F5"; onActivated: p.preview(0) }
    Shortcut { sequence: "Escape"; enabled: studio.busy; onActivated: studio.stop() }
    onClosing: function(event) { event.accepted = studio.requestClose() }
    Connections { target: studio; function onCloseReady() { Qt.quit() } }
    DropArea {
        id: videoDropArea; objectName: "fileDropArea"; anchors.fill: parent; z: 10
        onEntered: function(drag) {
            if (drag.hasUrls && !studio.busy) drag.accept(Qt.CopyAction)
            else drag.accepted = false
        }
        onDropped: function(drop) {
            if (drop.hasUrls && !studio.busy) {
                p.dropFiles(drop.urls)
                drop.accept(Qt.CopyAction)
            } else drop.accepted = false
        }
    }

    ColumnLayout {
        anchors.fill: parent; anchors.margins: 20; spacing: 14
        RowLayout {
            Layout.fillWidth: true; spacing: 14
            Rectangle { width: 42; height: 42; radius: 12; color: accent
                Text { anchors.centerIn: parent; text: "TS"; font.pixelSize: 17; font.bold: true; color: "#15210b" }
            }
            ColumnLayout { spacing: 1
                Label { text: "Template Studio"; color: ink; font.pixelSize: 23; font.bold: true }
                Caption { text: "Xuất video hàng loạt" }
            }
            Item { Layout.fillWidth: true }
            Action { text: "Cài đặt"; onClicked: settings.open() }
        }

        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 14
            Rectangle {
                objectName: "videoPanel"
                Layout.preferredWidth: 286; Layout.minimumWidth: 260; Layout.maximumWidth: 286
                Layout.fillHeight: true; radius: 14; color: "#151d2a"; border.color: videoDropArea.containsDrag ? accent : "#263246"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Label { text: "Danh sách video"; color: ink; font.pixelSize: 18; font.bold: true }
                    RowLayout { Layout.fillWidth: true
                        Action { objectName: "topImportButton"; text: "Thêm video"; Layout.fillWidth: true; enabled: !studio.busy; onClicked: p.importFiles() }
                        Action { text: "Thêm thư mục"; Layout.fillWidth: true; enabled: !studio.busy; onClicked: p.importFolder() }
                    }
                    Item {
                        objectName: "videoListArea"
                        Layout.fillWidth: true; Layout.fillHeight: true
                        MouseArea {
                            anchors.fill: parent; enabled: p.rows.length===0 && !studio.busy
                            cursorShape: Qt.PointingHandCursor
                            onClicked: p.importFiles()
                        }
                        ColumnLayout {
                            z: 1
                            anchors.centerIn: parent; width: parent.width; spacing: 14; visible: p.rows.length === 0
                            Rectangle { Layout.alignment: Qt.AlignHCenter; width: 64; height: 64; radius: 18; color: "#223328"
                                Text { anchors.centerIn: parent; text: "+"; color: accent; font.pixelSize: 38; font.weight: Font.Light }
                            }
                            Label { text: "Kéo video vào đây"; color: ink; font.pixelSize: 17; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Caption { text: "Hoặc thêm cả thư mục."; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                            Action { objectName: "emptyImportButton"; text: "Thêm video"; primary: true; Layout.alignment: Qt.AlignHCenter; enabled: !studio.busy; onClicked: p.importFiles() }
                        }
                        ListView {
                            id: queue; anchors.fill: parent; model: p.rows; visible: p.rows.length>0; clip: true; spacing: 8
                            ScrollBar.vertical: Scroller {}
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
                                        Check { checked: modelData.selected; enabled: !studio.busy; onClicked: p.toggle(index) }
                                        ColumnLayout { Layout.fillWidth: true; spacing: 4
                                            Label { text: modelData.name; color: ink; font.bold: true; font.pixelSize: 13; elide: Text.ElideMiddle; Layout.fillWidth: true
                                                ToolTip.visible: nameMouse.containsMouse; ToolTip.text: modelData.path
                                                MouseArea { id: nameMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                                            }
                                            Caption { text: modelData.meta; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                            Caption { text: modelData.presetName; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                                        }
                                    }
                                    RowLayout { Layout.fillWidth: true
                                        Caption { text: modelData.detail===modelData.status ? "" : modelData.detail; font.pixelSize: 11; color: modelData.status==="Lỗi" || modelData.status==="Thiếu nguồn" ? "#ff9c9c" : muted; elide: Text.ElideRight; Layout.fillWidth: true
                                            ToolTip.visible: detailMouse.containsMouse; ToolTip.text: modelData.detail || modelData.status
                                            MouseArea { id: detailMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                                        }
                                        Label { text: modelData.status==="Đang xuất" ? modelData.percent+"%" : win.statusText(modelData.status); color: modelData.status==="Hoàn tất" ? accent : muted; font.pixelSize: 11; Layout.alignment: Qt.AlignRight }
                                    }
                                    Progress { from: 0; to: 100; value: modelData.percent; Layout.fillWidth: true }
                                }
                            }
                        }
                    }
                    Caption { text: p.summary; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    Action { text: "Bỏ khỏi danh sách"; Layout.fillWidth: true; enabled: !studio.busy && p.rows.length>0; onClicked: p.removeSelected(); ToolTip.visible: hovered; ToolTip.text: "Bỏ mục đã chọn, giữ file trên máy." }
                    RowLayout { Layout.fillWidth: true; spacing: 8
                        Action { text: "Xuất lại"; Layout.fillWidth: true; leftPadding: 10; rightPadding: 10; font.pixelSize: 12; enabled: !studio.busy && p.rows.length>0; onClicked: p.retrySelected(); ToolTip.visible: hovered; ToolTip.text: "Xuất lại các mục đã chọn; nếu chưa chọn thì thử lại video lỗi." }
                        Action { text: "Ẩn video đã xuất"; Layout.fillWidth: true; leftPadding: 10; rightPadding: 10; font.pixelSize: 12; enabled: !studio.busy; onClicked: p.clearDone() }
                    }
                }
            }
            Rectangle {
                objectName: "configurationPanel"
                Layout.fillWidth: true; Layout.minimumWidth: 420; Layout.fillHeight: true
                color: "#151d2a"; radius: 14; border.color: "#3c4e44"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: 12
                    Label { text: "Thông số video"; color: ink; font.pixelSize: 20; font.bold: true }
                    Select {
                        id: presets; objectName: "presetSelect"; Layout.fillWidth: true; implicitHeight: 44; enabled: !studio.busy
                        model: p.presets; textRole: "name"; valueRole: "id"
                        currentIndex: { for (var i=0;i<p.presets.length;i++) if(p.presets[i].id===p.presetId)return i; return 0 }
                        onActivated: p.choosePreset(currentValue)
                    }
                    Caption { text: "Áp dụng cho tất cả video chưa xuất."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    ScrollView {
                        id: configurationScroll; objectName: "configurationScroll"
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; contentWidth: availableWidth
                        rightPadding: 14
                        ScrollBar.vertical: Scroller { objectName: "configurationBar"; x: configurationScroll.width-width; y: 0; height: configurationScroll.availableHeight; policy: ScrollBar.AlwaysOn }
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
                                        Select { objectName: "qualitySelect"; model: ["Tiết kiệm", "Tiêu chuẩn", "Chất lượng cao"]; property var ids: ["small","standard","high"]; currentIndex: ids.indexOf(p.config.quality); enabled: !studio.busy; onActivated: p.configure("quality",ids[currentIndex]); Layout.fillWidth: true }
                                        Caption { text: p.config.quality==="high" ? "Chất lượng cố định (CQ18)" : "Bitrate video (Mb/s)"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        Field { objectName: "bitrateField"; text: String(p.config.video_bitrate); visible: p.config.quality!=="high"; enabled: !studio.busy; validator: DoubleValidator { bottom: .5; top: 100; locale: "en_US" } onEditingFinished: p.configure("video_bitrate",Number(text)); Layout.fillWidth: true }
                                        Caption { text: "Bộ mã hóa" }
                                        Select { objectName: "encoderSelect"; model: ["Tự động", "NVIDIA NVENC", "CPU (x264)"]; property var ids: ["auto","h264_nvenc","libx264"]; currentIndex: ids.indexOf(p.config.encoder); enabled: !studio.busy; onActivated: p.configure("encoder",ids[currentIndex]); Layout.fillWidth: true }
                                        Caption { text: "Tỷ lệ khung / chiều rộng (px)"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                        RowLayout { Layout.fillWidth: true
                                            Select { objectName: "aspectSelect"; model: ["3:4","9:16"]; currentIndex: p.config.height/p.config.width>1.5 ? 1 : 0; enabled: !studio.busy; onActivated: p.configure("aspect",currentText); Layout.fillWidth: true }
                                            Select { objectName: "resolutionSelect"; model: ["1080","720"]; currentIndex: p.config.width===1080 ? 0 : 1; enabled: !studio.busy; onActivated: p.configure("resolution",Number(currentText)); Layout.fillWidth: true }
                                        }
                                        Check { text: "Tắt âm thanh"; checked: p.config.mute; enabled: !studio.busy; onClicked: p.configure("mute",checked) }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Hiệu ứng mở đầu" }
                                        Check { objectName: "introCheck"; text: "Bật hiệu ứng ngũ giác"; checked: p.config.intro_enabled; enabled: !studio.busy; onClicked: p.configure("intro_enabled",checked) }
                                        Caption { text: "Thời lượng: " + (p.config.effect_end-p.config.effect_start).toFixed(2) + " giây" }
                                        Range { from: 0; to: 8; value: p.config.effect_end; enabled: !studio.busy; onMoved: p.configure("effect_end",value); Layout.fillWidth: true }
                                        Caption { text: "Chuyển động: " + Math.round(p.config.effect_slider*100) + "%" }
                                        Range { from: 0; to: 1; value: p.config.effect_slider; enabled: !studio.busy; onMoved: p.configure("effect_slider",value); Layout.fillWidth: true }
                                        Caption { text: "Cỡ bokeh: " + p.config.bokeh_size.toFixed(2) }
                                        Range { from: 0; to: 1.5; value: p.config.bokeh_size; enabled: !studio.busy; onMoved: p.configure("bokeh_size",value); Layout.fillWidth: true }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Màu và nét" }
                                        Check { text: "Bật bộ lọc"; checked: p.config.filter_enabled; enabled: !studio.busy; onClicked: p.configure("filter_enabled",checked) }
                                        Caption { text: "Độ đậm màu: " + Math.round(p.config.filter_intensity*100) + "%" }
                                        Range { from: 0; to: 1; value: p.config.filter_intensity; enabled: !studio.busy; onMoved: p.configure("filter_intensity",value); Layout.fillWidth: true }
                                        Caption { text: "Độ nét: " + Math.round(p.config.sharpness*100) + "%" }
                                        Range { from: 0; to: 1; value: p.config.sharpness; enabled: !studio.busy; onMoved: p.configure("sharpness",value); Layout.fillWidth: true }
                                        Caption { text: "Phạm vi lọc màu" }
                                        Select { objectName: "skinSelect"; model: ["Toàn khung hình", "Tách vùng da theo màu"]; currentIndex: p.config.skin==="chroma" ? 1 : 0; enabled: !studio.busy; onActivated: p.configure("skin",currentIndex===1 ? "chroma" : "none"); Layout.fillWidth: true }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                                SettingsCard {
                                    contentItem: ColumnLayout { spacing: 8
                                        Section { text: "Bố cục và tốc độ" }
                                        Caption { text: "Phóng to: " + Math.round(p.config.scale*100) + "%" }
                                        Range { from: .3; to: 1.5; value: p.config.scale; enabled: !studio.busy; onMoved: p.configure("scale",value); Layout.fillWidth: true }
                                        Caption { text: "Vị trí ngang" }
                                        Range { from: -.3; to: .3; value: p.config.offset[0]; enabled: !studio.busy; onMoved: p.configure("offsetX",value); Layout.fillWidth: true }
                                        Caption { text: "Vị trí dọc" }
                                        Range { from: -.3; to: .3; value: p.config.offset[1]; enabled: !studio.busy; onMoved: p.configure("offsetY",value); Layout.fillWidth: true }
                                        Caption { text: "Độ mờ nền" }
                                        Range { from: 0; to: .1; value: p.config.background_sigma_ratio; enabled: !studio.busy; onMoved: p.configure("background_sigma_ratio",value); Layout.fillWidth: true }
                                        Check { text: "Lật ngang"; checked: p.config.flip; enabled: !studio.busy; onClicked: p.configure("flip",checked) }
                                        Caption { text: "Tốc độ video (×)" }
                                        Field { text: String(p.config.playback_rate); validator: DoubleValidator { bottom: .5; top: 2; locale: "en_US" } enabled: !studio.busy; onEditingFinished: p.configure("playback_rate",Number(text)); Layout.fillWidth: true }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }
                            SettingsCard {
                                objectName: "customPresetCard"
                                contentItem: ColumnLayout { spacing: 8
                                    Section { text: "Lưu preset" }
                                    RowLayout { Layout.fillWidth: true
                                        Field { id: presetName; placeholderText: "Tên preset"; Layout.fillWidth: true }
                                        Action { text: "Lưu preset"; enabled: !studio.busy && presetName.text.trim()!==""; onClicked: { p.savePreset(presetName.text);presetName.clear() } }
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
                        Label { text: "Xem trước"; color: ink; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true }
                        Check { objectName: "sourceCheck"; text: "Video gốc"; checked: p.sourceMode; onClicked: p.showSource(checked) }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d15"; radius: 10; clip: true
                        Video { id: previewPlayer; anchors.fill: parent; source: p.previewUrl; fillMode: VideoOutput.PreserveAspectFit; autoPlay: true; loops: MediaPlayer.Infinite; visible: p.previewUrl!=="" }
                        Column { anchors.centerIn: parent; width: parent.width-32; spacing: 12; visible: !previewPlayer.visible
                            Text { text: "▶"; color: "#7789a3"; font.pixelSize: 48; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                            Text { text: current ? "Bấm Xem thử để xem hiệu ứng." : "Chọn video trong danh sách."; color: muted; width: parent.width; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                        }
                        Rectangle { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8; height: staleText.implicitHeight+16; radius: 6; color: "#573d26"; visible: p.previewStale
                            Text { id: staleText; anchors.fill: parent; anchors.margins: 8; text: "Thông số đã đổi. Cần xem thử lại."; color: "#ffe0ae"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                    }
                    RowLayout { Layout.fillWidth: true
                        Action { text: previewPlayer.playbackState===MediaPlayer.PlayingState ? "Tạm dừng" : "Phát"; implicitWidth: 84; enabled: p.previewUrl!==""; onClicked: previewPlayer.playbackState===MediaPlayer.PlayingState ? previewPlayer.pause() : previewPlayer.play() }
                        Range { from: 0; to: Math.max(1,previewPlayer.duration); value: previewPlayer.position; onMoved: previewPlayer.seek(value); Layout.fillWidth: true; enabled: p.previewUrl!=="" }
                    }
                    Caption { text: win.timeText(previewPlayer.position)+" / "+win.timeText(previewPlayer.duration); Layout.alignment: Qt.AlignRight; visible: p.previewUrl!==""; font.pixelSize: 11 }
                    RowLayout { Layout.fillWidth: true
                        Caption { text: "Từ giây"; font.pixelSize: 12 }
                        NumberField { id: offset; objectName: "previewOffset"; from: 0; to: current ? Math.max(0,Math.floor(current.duration/p.config.playback_rate)-3) : 0; Layout.fillWidth: true }
                    }
                    Action { objectName: "previewButton"; text: "Xem thử 3 giây"; Layout.fillWidth: true; enabled: !studio.busy && p.ready && p.currentIndex>=0; onClicked: p.preview(offset.value) }
                    Action { text: "Mở video đã xuất"; Layout.fillWidth: true; enabled: current!==null && !!current.result; onClicked: p.openResult() }
                }
            }
        }

        Rectangle {
            objectName: "exportPanel"
            Layout.fillWidth: true; implicitHeight: exportLayout.implicitHeight+28; radius: 14; color: "#151e29"; border.color: "#34455a"
            ColumnLayout { id: exportLayout; anchors.fill: parent; anchors.margins: 14; spacing: 8
                RowLayout { Layout.fillWidth: true
                    Caption { text: "Thư mục xuất" }
                    Label { text: p.output; color: ink; elide: Text.ElideMiddle; Layout.fillWidth: true }
                    Action { text: "Chọn thư mục"; enabled: !studio.busy; onClicked: p.chooseOutput() }
                    Action { text: "Mở thư mục"; onClicked: p.openOutput() }
                }
                RowLayout { Layout.fillWidth: true; spacing: 16
                    ColumnLayout { Layout.fillWidth: true; spacing: 7
                        Label { text: studio.busy ? studio.notice : (!p.ready ? p.runtimeNotice : studio.notice); color: p.ready ? ink : "#e6c481"; wrapMode: Text.WordWrap; maximumLineCount: 2; elide: Text.ElideRight; Layout.fillWidth: true
                            ToolTip.visible: statusMouse.containsMouse; ToolTip.text: text
                            MouseArea { id: statusMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                        }
                        Progress { from: 0; to: 100; value: p.overall; Layout.fillWidth: true; visible: p.rows.length>0 }
                        Caption { text: p.estimate; visible: text!=="" }
                    }
                    Action { text: "Dừng sau video này"; visible: p.batchRunning; onClicked: p.stopAfterFile() }
                    Action { objectName: "exportButton"; text: studio.busy ? "Dừng" : "Xuất video"; primary: !studio.busy; danger: studio.busy; implicitWidth: 160; implicitHeight: 44
                        enabled: studio.busy || (p.ready && p.rows.length>0)
                        onClicked: studio.busy ? studio.stop() : p.runBatch()
                    }
                }
            }
        }
    }

    Drawer {
        id: settings; objectName: "systemDrawer"; edge: Qt.RightEdge; width: Math.min(660, win.width-80); height: win.height
        background: Rectangle { color: "#151d2a" }
        ScrollView { id: systemScroll; anchors.fill: parent; padding: 20; rightPadding: 34; clip: true; contentWidth: availableWidth
            ScrollBar.vertical: Scroller { x: systemScroll.width-width-8; y: systemScroll.topPadding; height: systemScroll.availableHeight }
            ColumnLayout { width: systemScroll.availableWidth; spacing: 10
                RowLayout { Layout.fillWidth: true
                    Label { text: "Cài đặt"; color: ink; font.pixelSize: 23; font.bold: true; Layout.fillWidth: true; topPadding: 20 }
                    Action { text: "Đóng"; onClicked: settings.close() }
                }
                Section { text: "GPU và hiệu ứng" }
                Caption { text: p.runtimeNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Caption { text: "Nhập file RAR hoặc thư mục hiệu ứng từ CapCut."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true
                    Action { text: "Chọn file RAR"; enabled: !studio.busy; onClicked: p.importAssets(); Layout.fillWidth: true }
                    Action { text: "Chọn thư mục hiệu ứng"; enabled: !studio.busy; onClicked: p.importAssetsFolder(); Layout.fillWidth: true }
                }
                Action { text: "Kiểm tra GPU"; enabled: !studio.busy; onClicked: p.checkRuntime(); Layout.fillWidth: true }
                Action { text: "Cài FFmpeg"; visible: !studio.mediaReady; enabled: !studio.busy; onClicked: studio.prepareMedia(); Layout.fillWidth: true }
                Section { text: "Phiên bản " + studio.version }
                Caption { text: studio.updateNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Action { text: "Kiểm tra cập nhật"; enabled: !studio.busy; onClicked: studio.checkUpdates(); Layout.fillWidth: true }
                Action { text: "Cập nhật và mở lại"; visible: studio.updateAvailable; enabled: !studio.busy; primary: true; onClicked: studio.installUpdate(); Layout.fillWidth: true }
                Action { text: "Mở nhật ký"; onClicked: p.openLogs(); Layout.fillWidth: true }
                Item { height: 20 }
            }
        }
    }
}
