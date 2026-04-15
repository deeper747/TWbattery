#!/bin/bash
# setup_reminder.sh — 設定每月 10 日的 macOS 更新提醒
# Sets a recurring monthly macOS Calendar reminder for data updates.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

osascript <<EOF
tell application "Calendar"
    -- Find or create a calendar named "Work"
    set targetCalendar to missing value
    repeat with c in (get every calendar)
        if (name of c) is "Work" or (name of c) is "工作" then
            set targetCalendar to c
            exit repeat
        end if
    end repeat
    if targetCalendar is missing value then
        set targetCalendar to make new calendar with properties {name:"Reminders"}
    end if

    -- Get next 10th of month
    set todayDate to (current date)
    set theYear to year of todayDate
    set theMonth to month of todayDate as integer
    if day of todayDate > 10 then
        set theMonth to theMonth + 1
        if theMonth > 12 then
            set theMonth to 1
            set theYear to theYear + 1
        end if
    end if
    set reminderDate to date (theMonth & "/10/" & theYear & " 09:00:00")

    -- Create recurring event
    set newEvent to make new event at end of events of targetCalendar with properties {
        summary:"🔋 更新台灣電池進出口資料",
        start date:reminderDate,
        end date:reminderDate + (30 * minutes),
        description:"1. 前往 portal.sw.nat.gov.tw/APGA/GA30 下載最新月份資料
2. 或執行: cd $PROJECT_DIR && python scripts/fetch_data.py
3. 執行: python scripts/process_data.py
4. 開啟: streamlit run dashboard.py

詳細說明: data/MANUAL_DOWNLOAD.md",
        recurrence:"RRULE:FREQ=MONTHLY;BYMONTHDAY=10"
    }
    log "✅ Reminder created: " & (summary of newEvent)
end tell
EOF

echo "✅ Monthly reminder set for the 10th of each month in Calendar.app"
echo "   (To delete: open Calendar.app and remove the '更新台灣電池進出口資料' event)"
