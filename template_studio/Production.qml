import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia

ApplicationWindow {
    id: win
    visible: true
    width: 1440; height: 900; minimumWidth: 1100; minimumHeight: 720
    title: "Beta Render"
    color: "#10181c"
    property var p: studio.production
    property color ink: "#edf2fc"
    property color muted: "#a0adc1"
    property color accent: "#73e9ce"
    property var current: p.currentIndex >= 0 && p.currentIndex < p.rows.length ? p.rows[p.currentIndex] : null
    palette.window: "#141b28"; palette.windowText: ink; palette.text: ink
    palette.base: "#0e1420"; palette.button: "#34474f"; palette.buttonText: ink
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
    function partLabels(count) {
        var labels=[]
        for(var i=0;i<count;i++)labels.push("Part "+(i+1))
        return labels
    }

    component Action: Button {
        id: b
        property bool primary: false
        property bool danger: false
        implicitHeight: 38; leftPadding: 12; rightPadding: 12; font.pixelSize: 13
        contentItem: Text { text: b.text; color: b.primary ? "#09221d" : (b.danger ? "#ffb9bd" : win.ink); font: b.font; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: b.enabled ? 1 : .5 }
        background: Rectangle { color: b.primary ? (b.down ? "#5bd8ba" : win.accent) : (b.danger ? "#482a31" : (b.down ? "#31515f" : b.hovered ? "#2a4654" : "#20323b")); border.color: b.visualFocus ? win.accent : (b.primary ? "transparent" : "#3d5966"); radius: 6; opacity: b.enabled ? 1 : .5 }
    }
    component Select: ComboBox {
        id: select
        property bool showDescriptions: false
        implicitHeight: 38; leftPadding: 12; rightPadding: 32; font.pixelSize: 13
        ToolTip.visible: hovered && !popup.visible
        ToolTip.delay: 700; ToolTip.text: displayText
        contentItem: Text { objectName: select.objectName+"Text"; text: select.displayText; font: select.font; color: select.enabled ? win.ink : "#8290a5"; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
        background: Rectangle { color: "#10232d"; border.color: select.visualFocus || select.popup.visible ? win.accent : (select.hovered ? "#63758e" : "#3c5966"); radius: 6; opacity: select.enabled ? 1 : .5 }
        indicator: Canvas {
            x: select.width-width-12; y: (select.height-height)/2; width: 10; height: 6; opacity: select.enabled ? 1 : .4
            onPaint: { var c=getContext("2d"); c.clearRect(0,0,width,height); c.strokeStyle="#b9c6d8"; c.lineWidth=1.6; c.beginPath(); c.moveTo(1,1); c.lineTo(5,5); c.lineTo(9,1); c.stroke() }
        }
        delegate: ItemDelegate {
            id: option
            required property var modelData
            required property int index
            property bool selected: select.currentIndex===index
            width: select.popup.availableWidth; height: select.showDescriptions ? Math.max(58,contentItem.implicitHeight+18) : 38; leftPadding: 10; rightPadding: 10
            highlighted: select.highlightedIndex===index
            contentItem: Text {
                objectName: "optionText"
                text: (select.textRole ? option.modelData[select.textRole] : option.modelData)+(select.showDescriptions && option.modelData.description ? "\n"+option.modelData.description : "")
                color: option.selected ? "#09221d" : "#edf2fc"
                font.pixelSize: 13; font.weight: option.selected ? Font.DemiBold : Font.Normal
                verticalAlignment: Text.AlignVCenter; wrapMode: select.showDescriptions ? Text.WordWrap : Text.NoWrap; elide: select.showDescriptions ? Text.ElideNone : Text.ElideRight
            }
            background: Rectangle { color: option.selected ? win.accent : (option.hovered || option.highlighted ? "#264857" : "transparent"); radius: 4 }
        }
        popup: Popup {
            objectName: select.objectName+"Popup"
            y: select.height+5; width: select.width; padding: 6
            implicitHeight: Math.min(contentItem.implicitHeight+12,select.showDescriptions ? Math.min(460,win.height-200) : 320)
            contentItem: ListView { clip: true; implicitHeight: contentHeight; model: select.popup.visible ? select.delegateModel : null; currentIndex: select.highlightedIndex; ScrollBar.vertical: Scroller {} }
            background: Rectangle { color: "#162b35"; border.color: "#476b7b"; radius: 8 }
        }
    }
    component Field: TextField {
        id: field
        implicitHeight: 38; leftPadding: 12; rightPadding: 12; font.pixelSize: 13
        color: enabled ? win.ink : "#8290a5"; placeholderTextColor: "#8c9bb0"
        selectByMouse: true; selectionColor: win.accent; selectedTextColor: "#09221d"
        background: Rectangle { color: "#10232d"; radius: 6; border.color: field.activeFocus ? win.accent : "#3c5966"; opacity: field.enabled ? 1 : .5 }
    }
    component ColorRow: RowLayout {
        id: colorRow
        required property string label
        required property string setting
        Layout.fillWidth: true
        Caption { text: colorRow.label; Layout.preferredWidth: 132 }
        Action {
            objectName: colorRow.setting+"Picker"; text: ""; implicitWidth: 46
            Accessible.name: "Chọn "+colorRow.label.toLowerCase(); enabled: !studio.busy
            Rectangle { anchors.centerIn: parent; width: 24; height: 20; radius: 3; border.color: "#a0adc1"; color: "#"+configDialog.draft[colorRow.setting]; opacity: studio.busy ? .5 : 1 }
            onClicked: {var value=p.chooseColor(configDialog.draft[colorRow.setting]);if(value)configDialog.edit(colorRow.setting,value)}
        }
        Field {
            objectName: colorRow.setting+"Field"; text: "#"+configDialog.draft[colorRow.setting]; Layout.fillWidth: true
            enabled: !studio.busy; maximumLength: 7
            validator: RegularExpressionValidator { regularExpression: /#?[0-9a-fA-F]{6}/ }
            onEditingFinished: {if(acceptableInput)configDialog.edit(colorRow.setting,text.replace(/^#/,"").toUpperCase());else text="#"+configDialog.draft[colorRow.setting]}
        }
    }
    component Range: Slider {
        id: range
        implicitHeight: 28; padding: 4
        background: Rectangle {
            x: range.leftPadding; y: range.topPadding+(range.availableHeight-height)/2
            width: range.availableWidth; height: 4; radius: 2; color: "#345566"
            Rectangle { width: range.visualPosition*parent.width; height: parent.height; radius: 2; color: range.enabled ? "#20c4dc" : "#526078" }
        }
        handle: Rectangle {
            x: range.leftPadding+range.visualPosition*(range.availableWidth-width); y: range.topPadding+(range.availableHeight-height)/2
            implicitWidth: 16; implicitHeight: 16; radius: 8
            color: range.enabled ? (range.pressed ? win.accent : "#20c4dc") : "#728097"
            border.color: range.visualFocus ? win.accent : "#53647c"; border.width: range.visualFocus ? 2 : 1
        }
    }
    component Check: CheckBox {
        id: check
        implicitHeight: 30; leftPadding: 2; rightPadding: 2; spacing: 8
        indicator: Rectangle {
            x: check.leftPadding; y: check.topPadding+(check.availableHeight-height)/2
            width: 18; height: 18; radius: 4; color: check.checked ? win.accent : "#10232d"
            border.color: check.checked || check.visualFocus ? win.accent : (check.hovered ? "#91a3bd" : "#476b7b")
            opacity: check.enabled ? 1 : .5
            Text { anchors.centerIn: parent; text: "✓"; color: "#09221d"; font.pixelSize: 14; font.bold: true; visible: check.checked }
        }
        contentItem: Text { text: check.text; font.pixelSize: 13; color: check.enabled ? win.ink : "#8290a5"; leftPadding: check.indicator.width+check.spacing; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
    }
    component NumberField: SpinBox {
        id: number
        implicitWidth: 84; implicitHeight: 38; leftPadding: 28; rightPadding: 28; font.pixelSize: 13
        editable: true
        contentItem: TextInput { text: number.textFromValue(number.value,number.locale); font: number.font; color: win.ink; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; readOnly: !number.editable; validator: number.validator; selectByMouse: true; selectionColor: win.accent; selectedTextColor: "#09221d"; inputMethodHints: Qt.ImhDigitsOnly }
        up.indicator: Rectangle { x: number.width-width; height: number.height; width: 28; color: number.up.pressed ? "#264857" : "transparent"; radius: 6; Text { anchors.centerIn: parent; text: "+"; color: number.up.enabled ? win.ink : win.muted; font.pixelSize: 18 } }
        down.indicator: Rectangle { x: 0; height: number.height; width: 28; color: number.down.pressed ? "#264857" : "transparent"; radius: 6; Text { anchors.centerIn: parent; text: "−"; color: number.down.enabled ? win.ink : win.muted; font.pixelSize: 18 } }
        background: Rectangle { color: "#10232d"; border.color: number.activeFocus ? win.accent : "#3c5966"; radius: 6 }
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

    component FoldSection: Pane {
        id: fold
        property string title
        property bool expanded: false
        default property alias fields: sectionFields.data
        Layout.fillWidth: true; padding: 0
        background: Item {}
        contentItem: ColumnLayout {
            spacing: 0
            Button {
                Layout.fillWidth: true; implicitHeight: 42; leftPadding: 14; rightPadding: 14
                contentItem: Text { text: (fold.expanded ? "⌄  " : "›  ")+fold.title; color: "#69deed"; font.family: win.font.family; font.pixelSize: 13; font.bold: true; verticalAlignment: Text.AlignVCenter }
                background: Rectangle { color: parent.hovered ? "#244858" : "#1c3b4b"; radius: 3; border.color: "#315566" }
                onClicked: fold.expanded=!fold.expanded
            }
            Pane {
                visible: fold.expanded; Layout.fillWidth: true; padding: 12
                background: Rectangle { color: "#102733"; border.color: "#315566"; radius: 3 }
                contentItem: ColumnLayout { id: sectionFields; spacing: 10 }
            }
        }
    }
    component SettingRow: RowLayout {
        id: row
        required property string label
        required property string setting
        property real low: 0
        property real high: 1
        property real factor: 1
        property int decimals: 0
        property string unit: ""
        property real number: configDialog.read(setting)
        Layout.fillWidth: true; spacing: 10
        Label { text: row.label; color: win.ink; font.pixelSize: 13; Layout.preferredWidth: 132; wrapMode: Text.WordWrap }
        Range { objectName: row.setting+"Slider"; Layout.fillWidth: true; from: row.low; to: row.high; value: row.number; enabled: !studio.busy; onMoved: configDialog.edit(row.setting,value) }
        Field {
            objectName: row.setting+"Field"
            property bool dirty: false
            Layout.preferredWidth: 76; horizontalAlignment: Text.AlignRight
            text: (row.number*row.factor).toFixed(row.decimals)
            validator: DoubleValidator { bottom: row.low*row.factor; top: row.high*row.factor; decimals: row.decimals; locale: "en_US" }
            enabled: !studio.busy
            onTextEdited: dirty=true
            onEditingFinished: {
                if (dirty && acceptableInput) configDialog.edit(row.setting,Number(text)/row.factor)
                dirty=false
                text=Qt.binding(function() {return (row.number*row.factor).toFixed(row.decimals)})
            }
        }
        Caption { text: row.unit; Layout.preferredWidth: 24 }
    }

    Shortcut { sequence: "Ctrl+O"; enabled: !configDialog.visible; onActivated: p.importFiles() }
    Shortcut { sequence: "Ctrl+Shift+O"; enabled: !configDialog.visible; onActivated: p.importFolder() }
    Shortcut { sequence: "Ctrl+Return"; enabled: !configDialog.visible; onActivated: p.runBatch() }
    Shortcut { sequence: "F5"; enabled: !configDialog.visible; onActivated: p.preview(0) }
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
            if (drop.hasUrls && !studio.busy) { p.dropFiles(drop.urls); drop.accept(Qt.CopyAction) }
            else drop.accepted = false
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 12; spacing: 12
        RowLayout {
            Layout.fillWidth: true
            Image {
                objectName: "appLogo"
                source: "assets/beta-render.png"
                Layout.preferredWidth: 48; Layout.preferredHeight: 48
                fillMode: Image.PreserveAspectFit; mipmap: true
                Accessible.name: "Logo Beta Render"
            }
            ColumnLayout { spacing: 2
                Label { text: "Beta Render"; color: ink; font.pixelSize: 24; font.bold: true }
                Caption { text: "Xử lý video hàng loạt" }
            }
            Item { Layout.fillWidth: true }
            Caption { text: p.ready ? "GPU sẵn sàng" : p.runtimeNotice; color: accent; elide: Text.ElideRight; Layout.maximumWidth: 350 }
            Action { text: "Cập nhật app"; visible: studio.updateAvailable; enabled: !studio.busy; primary: true; onClicked: studio.installUpdate() }
            Action { text: "Cài đặt"; onClicked: settings.open() }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Rectangle {
                objectName: "videoPanel"
                Layout.preferredWidth: 286; Layout.minimumWidth: 260; Layout.maximumWidth: 286
                Layout.fillHeight: true; radius: 5; color: "#192328"; border.color: videoDropArea.containsDrag ? accent : "#34474f"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 14; spacing: 12
                    Label { text: "01  Nguồn video"; color: ink; font.pixelSize: 18; font.bold: true }
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
                                width: queue.width; height: 126; radius: 4
                                color: index===p.currentIndex ? "#263449" : "#1c2b32"
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
                                            Caption { text: modelData.presetName; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true
                                                ToolTip.visible: presetMouse.containsMouse; ToolTip.text: text
                                                MouseArea { id: presetMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                                            }
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
                    Action { objectName: "errorLogButton"; text: "Nhật ký lỗi"; Layout.fillWidth: true; visible: p.currentIndex>=0 && p.currentIndex<p.rows.length && p.rows[p.currentIndex].status==="Lỗi"; onClicked: p.openErrorLog() }
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
                color: "#192328"; radius: 5; border.color: "#34474f"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 18; spacing: win.height<800 ? 10 : 16
                    Label { text: "02  Cấu hình chung"; color: ink; font.pixelSize: 18; font.bold: true }
                    Select {
                        id: presets; objectName: "presetSelect"; Layout.fillWidth: true; enabled: !studio.busy; showDescriptions: true
                        model: p.mainPresets; textRole: "name"; valueRole: "id"
                        currentIndex: {for(var i=0;i<p.mainPresets.length;i++)if(p.mainPresets[i].id===p.presetId)return i;return -1}
                        displayText: p.presetName
                        onActivated: p.choosePreset(currentValue)
                    }
                    Label { text: "Hiệu ứng: "+(p.config.intro_enabled ? p.effectName : "Tắt")+" · "+p.config.playback_rate.toFixed(2)+"×"; color: ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: (p.config.height/p.config.width>1.5 ? "9:16" : "3:4")+" · "+p.config.width+" × "+p.config.height+" · "+p.config.fps+" FPS · "+(p.config.mute ? "Tắt âm thanh" : "Giữ âm thanh gốc"); color: ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "H.264 · "+(p.config.quality==="high" ? "CQ18" : (p.config.video_bitrate*(p.config.quality==="small" ? .6 : 1)).toFixed(2)+" Mb/s")+" · "+(p.config.encoder==="auto" ? "Encoder tự động" : p.config.encoder==="h264_nvenc" ? "NVENC" : "CPU"); color: ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Bộ lọc: "+(p.config.filter_enabled ? p.filterName+" · "+Math.round(p.config.filter_intensity*100)+"% · Độ nét "+Math.round(p.config.sharpness*100)+"%" : "Tắt"); color: ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Label { text: "Phụ đề: "+({"auto":"Tự nhận lời thoại","file":"File đã chọn","sidecar":"File cạnh video","off":"Tắt"})[p.config.subtitle_mode]+" · "+(p.config.part_count===0 ? "Tự chia part" : p.config.part_count===1 ? "Xuất 1 video" : "Xuất "+p.config.part_count+" phần"); visible: p.config.subtitle_mode!=="off" || p.config.part_count!==1; color: ink; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Action { objectName: "editConfigButton"; text: "Chỉnh cấu hình…"; primary: true; Layout.fillWidth: true; topPadding: 12; bottomPadding: 12; enabled: !studio.busy; onClicked: configDialog.open() }
                    Caption { text: p.config.part_count===0 ? "Khoảng "+p.config.part_seconds+" giây/part, ưu tiên khoảng nghỉ lời thoại gần mốc cắt." : p.config.part_count>1 ? "Chia thành "+p.config.part_count+" phần đều nhau." : p.config.height/p.config.width>1.5 ? "Xuất video dọc 9:16 để đăng TikTok." : "Xuất video khung 3:4."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Caption { text: "Áp dụng cho các video chưa xuất."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    Item { Layout.preferredHeight: 8 }
                    Label { text: "Lưu cấu hình thành preset"; color: ink; font.pixelSize: 13; font.bold: true }
                    RowLayout { Layout.fillWidth: true
                        Field { id: presetName; placeholderText: "Tên preset"; Layout.fillWidth: true }
                        Action { text: "Lưu preset"; enabled: !studio.busy && presetName.text.trim()!==""; onClicked: {p.savePreset(presetName.text);presetName.clear()} }
                    }
                    RowLayout { objectName: "presetActions"; Layout.fillWidth: true
                        Action { text: "Nhập preset"; enabled: !studio.busy; onClicked: p.importPreset() }
                        Action { text: "Xuất preset"; enabled: !studio.busy; onClicked: p.exportPreset() }
                        Item { Layout.fillWidth: true }
                    }
                    Item { Layout.fillHeight: true }
                }
            }
            Rectangle {
                objectName: "previewPanel"
                Layout.preferredWidth: 312; Layout.minimumWidth: 270; Layout.maximumWidth: 350
                Layout.fillHeight: true; color: "#192328"; radius: 5; border.color: "#34474f"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 10
                    RowLayout { Layout.fillWidth: true
                        Label { text: "03  Xem trước"; color: ink; font.bold: true; font.pixelSize: 18; Layout.fillWidth: true }
                        Check { objectName: "sourceCheck"; text: "Video gốc"; checked: p.sourceMode; onClicked: p.showSource(checked) }
                    }
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true; color: "#080d15"; radius: 4; clip: true
                        Video { id: previewPlayer; objectName: "previewPlayer"; anchors.fill: parent; source: p.previewUrl; fillMode: VideoOutput.PreserveAspectFit; autoPlay: true; loops: 1; endOfStreamPolicy: VideoOutput.KeepLastFrame; visible: p.previewUrl!=="" }
                        Column { anchors.centerIn: parent; width: parent.width-32; spacing: 12; visible: !previewPlayer.visible
                            Text { text: "▶"; color: "#7789a3"; font.pixelSize: 48; width: parent.width; horizontalAlignment: Text.AlignHCenter }
                            Text { text: current ? "Bấm Xem thử để xem hiệu ứng." : "Chọn video trong danh sách."; color: muted; width: parent.width; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter }
                        }
                        Rectangle { anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 8; height: staleText.implicitHeight+16; radius: 6; color: "#573d26"; visible: p.previewStale
                            Text { id: staleText; anchors.fill: parent; anchors.margins: 8; text: "Thông số đã đổi. Cần xem thử lại."; color: "#ffe0ae"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                        }
                    }
                    RowLayout { Layout.fillWidth: true
                        Action { objectName: "playPreviewButton"; text: previewPlayer.playbackState===MediaPlayer.PlayingState ? "Tạm dừng" : "Phát"; implicitWidth: 84; enabled: p.previewUrl!==""; onClicked: previewPlayer.playbackState===MediaPlayer.PlayingState ? previewPlayer.pause() : previewPlayer.play() }
                        Range { from: 0; to: Math.max(1,previewPlayer.duration); value: previewPlayer.position; onMoved: previewPlayer.seek(value); Layout.fillWidth: true; enabled: p.previewUrl!=="" }
                    }
                    Caption { text: win.timeText(previewPlayer.position)+" / "+win.timeText(previewPlayer.duration); Layout.alignment: Qt.AlignRight; visible: p.previewUrl!==""; font.pixelSize: 11 }
                    RowLayout { Layout.fillWidth: true
                        Caption { text: "Từ giây"; font.pixelSize: 12 }
                        NumberField { id: offset; objectName: "previewOffset"; from: 0; to: current ? Math.max(0,Math.floor((current.duration-p.config.source_offset)/p.config.playback_rate)-3) : 0; Layout.fillWidth: true }
                    }
                    Action { objectName: "previewButton"; text: "Xem thử 3 giây"; Layout.fillWidth: true; enabled: !studio.busy && p.ready && p.currentIndex>=0; onClicked: p.preview(offset.value) }
                    Action { text: "Mở video đã xuất"; Layout.fillWidth: true; enabled: current!==null && !!current.result; onClicked: p.openResult() }
                    RowLayout { Layout.fillWidth: true; visible: current!==null && current.parts!==undefined && current.parts.length>1
                        Select { id: partResultSelect; objectName: "partResultSelect"; model: win.partLabels(current && current.parts ? current.parts.length : 0); Layout.fillWidth: true }
                        Action { text: "Mở part"; onClicked: p.openPart(partResultSelect.currentIndex) }
                    }
                }
            }
        }

        Rectangle {
            objectName: "exportPanel"
            Layout.fillWidth: true; implicitHeight: exportLayout.implicitHeight+28; radius: 5; color: "#192328"; border.color: "#34474f"
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

    Dialog {
        id: configDialog; objectName: "configDialog"
        anchors.centerIn: Overlay.overlay
        width: Math.min(850,win.width-60); height: Math.min(840,win.height-50)
        modal: true; padding: 16; closePolicy: Popup.CloseOnEscape
        property var draft: JSON.parse(JSON.stringify(p.config))
        property string error: ""
        function read(key) {
            if(key==="offsetX")return draft.offset[0]
            if(key==="offsetY")return draft.offset[1]
            if(key==="effect_duration")return draft.effect_end-draft.effect_start
            return Number(draft[key])
        }
        function edit(key,value) {
            var s=JSON.parse(JSON.stringify(draft))
            if(key==="offsetX" || key==="offsetY")s.offset[key==="offsetX" ? 0 : 1]=value
            else if(key==="effect_duration")s.effect_end=s.effect_start+value
            else if(key==="aspect")s.height=Math.round(s.width*(value==="9:16" ? 16/9 : 4/3))
            else if(key==="resolution"){var ratio=s.height/s.width;s.width=value;s.height=Math.round(value*ratio)}
            else s[key]=value
            draft=s
        }
        onOpened: {draft=JSON.parse(JSON.stringify(p.config));error=""}
        background: Rectangle { color: "#0b1b25"; border.color: "#40616f"; radius: 5 }
        Overlay.modal: Rectangle { color: "#a0000000" }
        contentItem: ColumnLayout {
            spacing: 12
            RowLayout { Layout.fillWidth: true
                Label { text: "Cấu hình chung"; color: ink; font.pixelSize: 19; font.bold: true; Layout.fillWidth: true }
                Action { text: "Đóng"; onClicked: configDialog.close() }
            }
            ScrollView {
                id: configurationScroll; objectName: "configurationScroll"
                Layout.fillWidth: true; Layout.fillHeight: true; contentWidth: availableWidth; rightPadding: 14; clip: true
                ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
                ScrollBar.vertical: Scroller { objectName: "configurationBar"; x: configurationScroll.width-width; y: 0; height: configurationScroll.availableHeight; policy: ScrollBar.AlwaysOn }
                ColumnLayout { width: configurationScroll.availableWidth; spacing: 8
                    FoldSection { objectName: "videoSection"; title: "Thiết lập video"; expanded: true
                        SettingRow { label: "Tốc độ"; setting: "playback_rate"; low: .5; high: 2; decimals: 2; unit: "×" }
                        SettingRow { label: "Tỷ lệ phóng to"; setting: "scale"; low: .3; high: 1.5; factor: 100; unit: "%" }
                        SettingRow { label: "Vị trí ngang"; setting: "offsetX"; low: -.3; high: .3; factor: 100; decimals: 1; unit: "%" }
                        SettingRow { label: "Vị trí dọc"; setting: "offsetY"; low: -.3; high: .3; factor: 100; decimals: 1; unit: "%" }
                        SettingRow { label: "Độ nghiêng video"; setting: "rotation_deg"; low: -30; high: 30; decimals: 1; unit: "°" }
                        SettingRow { label: "Độ mờ nền"; setting: "background_sigma_ratio"; low: 0; high: .1; factor: 100; decimals: 1; unit: "%" }
                        Check { text: "Lật ngang"; checked: configDialog.draft.flip; enabled: !studio.busy; onClicked: configDialog.edit("flip",checked) }
                        Check { text: "Giữ âm thanh gốc"; checked: !configDialog.draft.mute; enabled: !studio.busy; onClicked: configDialog.edit("mute",!checked) }
                        SettingRow { label: "Độ trễ âm thanh"; setting: "audio_delay_ms"; low: -1000; high: 1000; decimals: 0; unit: "ms"; visible: !configDialog.draft.mute }
                    }
                    FoldSection { objectName: "introSection"; title: p.effectName; expanded: true
                        Check { objectName: "introCheck"; text: "Bật hiệu ứng"; checked: configDialog.draft.intro_enabled; enabled: !studio.busy; onClicked: configDialog.edit("intro_enabled",checked) }
                        Check { text: "Lặp lại hiệu ứng"; checked: configDialog.draft.effect_loop_seconds>0; enabled: !studio.busy; onClicked: { configDialog.edit("effect_loop_seconds",checked ? 2.166667 : 0); configDialog.edit("effect_end",checked ? 3600 : 2.166667) } }
                        SettingRow { label: "Thời lượng"; setting: "effect_duration"; low: 0; high: 8; decimals: 2; unit: "s"; visible: configDialog.draft.effect_loop_seconds===0 }
                        SettingRow { label: "Lặp mỗi"; setting: "effect_loop_seconds"; low: 1; high: 10; decimals: 2; unit: "s"; visible: configDialog.draft.effect_loop_seconds>0 }
                        SettingRow { label: "Chuyển động"; setting: "effect_slider"; factor: 100; unit: "%" }
                        SettingRow { label: "Cỡ bokeh"; setting: "bokeh_size"; low: 0; high: 1.5; factor: 100; unit: "%" }
                    }
                    FoldSection { objectName: "captionsSection"; title: "Phụ đề karaoke"; expanded: p.config.subtitle_mode!=="off"
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Nguồn phụ đề"; Layout.preferredWidth: 132 }
                            Select { objectName: "subtitleMode"; model: ["Tắt", "File cạnh video", "Chọn file", "Tự nhận lời thoại"]
                                property var ids: ["off", "sidecar", "file", "auto"]
                                currentIndex: ids.indexOf(configDialog.draft.subtitle_mode)
                                enabled: !studio.busy
                                onActivated: configDialog.edit("subtitle_mode", ids[currentIndex]); Layout.fillWidth: true }
                        }
                        RowLayout { visible: configDialog.draft.subtitle_mode==="file"; Layout.fillWidth: true
                            Field { objectName: "subtitleFile"; placeholderText: "SRT, JSON từng từ hoặc draft_content.json"; Layout.fillWidth: true
                                text: configDialog.draft.subtitle_file; enabled: !studio.busy
                                onEditingFinished: configDialog.edit("subtitle_file", text) }
                            Action { objectName: "subtitlePicker"; text: "Chọn file…"; enabled: !studio.busy; onClicked: { var path=p.chooseSubtitleFile(); if(path)configDialog.edit("subtitle_file",path) } }
                        }
                        Check { objectName: "titleFromFile"; text: "Dùng tên video làm tiêu đề"; checked: configDialog.draft.subtitle_title==="{video}"; enabled: !studio.busy; onClicked: configDialog.edit("subtitle_title",checked ? "{video}" : "") }
                        Field { objectName: "subtitleTitle"; placeholderText: "Tiêu đề trên cùng (để trống để tắt)"; visible: configDialog.draft.subtitle_title!=="{video}"
                            Layout.fillWidth: true; text: configDialog.draft.subtitle_title; enabled: !studio.busy
                            onEditingFinished: configDialog.edit("subtitle_title", text) }
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Font chữ"; Layout.preferredWidth: 132 }
                            Field { objectName: "subtitleFontName"; text: configDialog.draft.subtitle_font_name; readOnly: true; Layout.fillWidth: true }
                            Action { objectName: "subtitleFontPicker"; text: "Chọn font…"; enabled: !studio.busy
                                onClicked: {var font=p.chooseSubtitleFont();if(font.path){configDialog.edit("subtitle_font_file",font.path);configDialog.edit("subtitle_font_name",font.name)}} }
                            Action { objectName: "subtitleFontReset"; text: "Mặc định"; enabled: !studio.busy
                                onClicked: {configDialog.edit("subtitle_font_file","");configDialog.edit("subtitle_font_name","Arial Black")} }
                        }
                        Check { objectName: "subtitleKeywords"; text: "Nhấn màu từ khóa"; checked: configDialog.draft.subtitle_keywords; enabled: !studio.busy; onClicked: configDialog.edit("subtitle_keywords",checked) }
                        Check { objectName: "subtitleEmoji"; text: "Emoji theo từ khóa"; checked: configDialog.draft.subtitle_emoji; enabled: !studio.busy; onClicked: configDialog.edit("subtitle_emoji",checked) }
                        SettingRow { label: "Độ nghiêng phụ đề"; setting: "subtitle_angle"; low: -30; high: 30; decimals: 1; unit: "°" }
                        ColorRow { label: "Chữ phụ đề"; setting: "subtitle_color" }
                        ColorRow { label: "Từ đang đọc"; setting: "subtitle_red" }
                        ColorRow { label: "Viền phụ đề"; setting: "subtitle_outline" }
                        ColorRow { label: "Chữ tiêu đề/PART"; setting: "title_color" }
                        ColorRow { label: "Nền tiêu đề/PART"; setting: "title_background" }
                        Caption { text: configDialog.draft.subtitle_mode==="auto" ? "Tự nhận lời thoại trên máy. Lần đầu tải bộ nhận giọng nói khoảng 150 MB; những lần sau dùng lại. Kiểm tra lời và thời điểm bằng bản xem thử." : "Draft giữ lời và mốc từng từ, quy đổi về video gốc. Chỉ hỗ trợ Draft dựng từ một nguồn. SRT ước lượng mốc từng từ."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                        Caption { text: "Màu và emoji chọn theo từ khóa, có thể tắt riêng. Font đã chọn được lưu trong dữ liệu app."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    }
                    FoldSection { objectName: "colorSection"; title: p.filterName
                        Check { text: "Bật bộ lọc"; checked: configDialog.draft.filter_enabled; enabled: !studio.busy; onClicked: configDialog.edit("filter_enabled",checked) }
                        SettingRow { label: "Độ đậm màu"; setting: "filter_intensity"; factor: 100; unit: "%" }
                        SettingRow { label: "Độ nét"; setting: "sharpness"; factor: 100; unit: "%" }
                        Select { objectName: "skinSelect"; model: ["Toàn khung hình","Tách vùng da theo màu"]; currentIndex: configDialog.draft.skin==="chroma" ? 1 : 0; enabled: !studio.busy; onActivated: configDialog.edit("skin",currentIndex===1 ? "chroma" : "none"); Layout.fillWidth: true }
                    }
                    FoldSection { objectName: "outputSection"; title: "Thiết lập đầu ra"; expanded: true
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Chia video"; Layout.preferredWidth: 132 }
                            Select { objectName: "partCountSelect"; model: ["Tự chia theo thời lượng", "1 video", "Chọn số part"]; currentIndex: configDialog.draft.part_count===0 ? 0 : configDialog.draft.part_count===1 ? 1 : 2; enabled: !studio.busy; onActivated: configDialog.edit("part_count",currentIndex<2 ? currentIndex : Math.max(2,configDialog.draft.part_count)); Layout.fillWidth: true }
                        }
                        RowLayout { Layout.fillWidth: true; visible: configDialog.draft.part_count>1
                            Caption { text: "Số part"; Layout.preferredWidth: 132 }
                            Field { objectName: "partCountField"; text: String(configDialog.draft.part_count); validator: IntValidator {bottom:2;top:100} enabled: !studio.busy; Layout.fillWidth: true
                                onEditingFinished: {if(acceptableInput)configDialog.edit("part_count",Number(text));else text=String(configDialog.draft.part_count)} }
                        }
                        RowLayout { Layout.fillWidth: true; visible: configDialog.draft.part_count===0
                            Caption { text: "Giây mỗi part"; Layout.preferredWidth: 132 }
                            Field { objectName: "partSecondsField"; text: String(configDialog.draft.part_seconds); validator: IntValidator {bottom:30;top:1800} enabled: !studio.busy; onEditingFinished: if(acceptableInput)configDialog.edit("part_seconds",Number(text)); Layout.fillWidth: true }
                        }
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Chất lượng"; Layout.preferredWidth: 132 }
                            Select { objectName: "qualitySelect"; model: ["Tiết kiệm","Tiêu chuẩn","Chất lượng cao"]; property var ids: ["small","standard","high"]; currentIndex: ids.indexOf(configDialog.draft.quality); enabled: !studio.busy; onActivated: configDialog.edit("quality",ids[currentIndex]); Layout.fillWidth: true }
                        }
                        RowLayout { Layout.fillWidth: true; visible: configDialog.draft.quality!=="high"
                            Caption { text: "Bitrate (Mb/s)"; Layout.preferredWidth: 132 }
                            Field { objectName: "bitrateField"; text: String(configDialog.draft.video_bitrate); validator: DoubleValidator {bottom:.5;top:100;locale:"en_US"} enabled: !studio.busy; onEditingFinished: if(acceptableInput)configDialog.edit("video_bitrate",Number(text)); Layout.fillWidth: true }
                        }
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Bộ mã hóa"; Layout.preferredWidth: 132 }
                            Select { objectName: "encoderSelect"; model: ["Tự động","NVIDIA NVENC","CPU (x264)"]; property var ids: ["auto","h264_nvenc","libx264"]; currentIndex: ids.indexOf(configDialog.draft.encoder); enabled: !studio.busy; onActivated: configDialog.edit("encoder",ids[currentIndex]); Layout.fillWidth: true }
                        }
                        RowLayout { Layout.fillWidth: true
                            Caption { text: "Khung hình"; Layout.preferredWidth: 132 }
                            Select { objectName: "aspectSelect"; model: ["3:4","9:16"]; currentIndex: configDialog.draft.height/configDialog.draft.width>1.5 ? 1 : 0; enabled: !studio.busy; onActivated: configDialog.edit("aspect",currentText); Layout.fillWidth: true }
                            Select { objectName: "resolutionSelect"; model: ["1080","720"]; currentIndex: configDialog.draft.width===1080 ? 0 : 1; enabled: !studio.busy; onActivated: configDialog.edit("resolution",Number(currentText)); Layout.fillWidth: true }
                            Caption { text: "px" }
                        }
                    }
                }
            }
            Caption { text: configDialog.error || "Lưu để áp dụng cho các video chưa xuất."; color: configDialog.error ? "#ffb9bd" : muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout { Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Action { objectName: "cancelConfigButton"; text: "Hủy"; onClicked: configDialog.close() }
                Action { objectName: "saveConfigButton"; text: "Lưu thay đổi"; primary: true; enabled: !studio.busy; onClicked: {if(p.applyConfig(configDialog.draft))configDialog.close();else configDialog.error=studio.notice} }
            }
        }
    }

    Drawer {
        id: settings; objectName: "systemDrawer"; edge: Qt.RightEdge; width: Math.min(660, win.width-80); height: win.height
        background: Rectangle { color: "#192328" }
        ScrollView { id: systemScroll; anchors.fill: parent; padding: 20; rightPadding: 34; clip: true; contentWidth: availableWidth
            ScrollBar.vertical: Scroller { x: systemScroll.width-width-8; y: systemScroll.topPadding; height: systemScroll.availableHeight }
            ColumnLayout { width: systemScroll.availableWidth; spacing: 10
                RowLayout { Layout.fillWidth: true
                    Label { text: "Cài đặt"; color: ink; font.pixelSize: 23; font.bold: true; Layout.fillWidth: true; topPadding: 20 }
                    Action { text: "Đóng"; onClicked: settings.close() }
                }
                Section { text: "GPU và hiệu ứng" }
                Caption { text: p.runtimeNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Caption { text: "Hiệu ứng đã có sẵn trong app. Có thể nhập gói khác để thay thế."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                RowLayout { Layout.fillWidth: true
                    Action { text: "Chọn file RAR"; enabled: !studio.busy; onClicked: p.importAssets(); Layout.fillWidth: true }
                    Action { text: "Chọn thư mục hiệu ứng"; enabled: !studio.busy; onClicked: p.importAssetsFolder(); Layout.fillWidth: true }
                }
                Action { text: "Kiểm tra GPU"; enabled: !studio.busy; onClicked: p.checkRuntime(); Layout.fillWidth: true }
                Action { text: "Cài FFmpeg"; visible: !studio.mediaReady; enabled: !studio.busy; onClicked: studio.prepareMedia(); Layout.fillWidth: true }
                Section { text: "Đối chiếu video mẫu" }
                Caption { text: "Khung 3:4 dùng để kiểm tra với bản CapCut đã xuất. Chọn preset TikTok ở màn hình chính để xuất video dọc 9:16."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Action { text: "Dùng cấu hình video mẫu 3:4"; enabled: !studio.busy; Layout.fillWidth: true; onClicked: {p.choosePreset("reference");settings.close()} }
                Section { text: "Phiên bản " + studio.version }
                Caption { text: "Emoji: Twemoji © Twitter và các tác giả, CC-BY-4.0."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Caption { text: studio.updateNotice; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Action { text: "Kiểm tra cập nhật"; enabled: !studio.busy; onClicked: studio.checkUpdates(); Layout.fillWidth: true }
                Action { text: "Cập nhật và mở lại"; visible: studio.updateAvailable; enabled: !studio.busy; primary: true; onClicked: studio.installUpdate(); Layout.fillWidth: true }
                Action { text: "Mở nhật ký"; onClicked: p.openLogs(); Layout.fillWidth: true }
                Item { height: 20 }
            }
        }
    }
}
