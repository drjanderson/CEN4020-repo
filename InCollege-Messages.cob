      *>*******************************************************
      *> Epic #8 private messaging menu and message sender.
      *> Messages are limited to accepted connections and are
      *> appended to InCollege-Messages.txt for later retrieval.
      *>*******************************************************
       >>SOURCE FORMAT FREE
       IDENTIFICATION DIVISION.
       PROGRAM-ID. MESSAGE-MENU.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       COPY "InCollege-Common.cpy".

       01  WS-MESSAGE                  PIC X(100).
       01  WS-LINE-TEXT                PIC X(100).
       01  WS-CHOICE                   PIC X(20).
       01  WS-BACK-FLAG                PIC X VALUE 'N'.
           88  BACK-REQUESTED                    VALUE 'Y'.

       PROCEDURE DIVISION.
       MESSAGE-MENU-START.
           MOVE 'N' TO WS-BACK-FLAG
           PERFORM UNTIL BACK-REQUESTED OR END-OF-INPUT
               MOVE "--- Messages Menu ---" TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               MOVE "1. Send a New Message" TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               MOVE "2. View My Messages" TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               MOVE "3. Back to Main Menu" TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               MOVE "Enter your choice:" TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               CALL "READ-LINE" USING WS-LINE-TEXT
               IF NOT END-OF-INPUT
                   MOVE WS-LINE-TEXT TO WS-CHOICE
                   EVALUATE FUNCTION TRIM(WS-CHOICE)
                       WHEN "1"
                           CALL "SEND-MESSAGE"
                       WHEN "2"
                           MOVE "View My Messages is under construction."
                               TO WS-MESSAGE
                           CALL "WRITE-LINE" USING WS-MESSAGE
                       WHEN "3"
                           MOVE 'Y' TO WS-BACK-FLAG
                       WHEN OTHER
                           MOVE "Invalid choice, please try again."
                               TO WS-MESSAGE
                           CALL "WRITE-LINE" USING WS-MESSAGE
                   END-EVALUATE
               END-IF
           END-PERFORM.
           GOBACK.
       END PROGRAM MESSAGE-MENU.

       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEND-MESSAGE.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT MESSAGE-FILE ASSIGN TO "InCollege-Messages.txt"
               ORGANIZATION IS LINE SEQUENTIAL
               FILE STATUS IS WS-MESSAGE-FILE-STATUS.

       DATA DIVISION.
       FILE SECTION.
       FD  MESSAGE-FILE.
       COPY "InCollege-MessageRecord.cpy".

       WORKING-STORAGE SECTION.
       COPY "InCollege-Common.cpy".
       COPY "InCollege-PendingRequestTable.cpy".

       01  WS-MESSAGE-FILE-STATUS      PIC X(2).
       01  WS-MESSAGE                  PIC X(100).
       01  WS-LINE-TEXT                PIC X(100).
       01  WS-RECIPIENT                PIC X(20).
       01  WS-CONTENT                  PIC X(250).
       01  WS-REQUEST-IDX              PIC 9(2).
       01  WS-CONNECTED                PIC X VALUE 'N'.
       01  WS-SAVE-OK                  PIC X VALUE 'N'.

       PROCEDURE DIVISION.
       SEND-MESSAGE-START.
           MOVE "Enter recipient's username (must be a connection):"
               TO WS-MESSAGE
           CALL "WRITE-LINE" USING WS-MESSAGE
           CALL "READ-LINE" USING WS-LINE-TEXT
           IF END-OF-INPUT
               GOBACK
           END-IF
           MOVE FUNCTION TRIM(WS-LINE-TEXT) TO WS-RECIPIENT

           PERFORM VALIDATE-CONNECTION
           IF WS-CONNECTED = 'N'
               MOVE "You can only message users you are connected with."
                   TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               GOBACK
           END-IF

           MOVE "Enter your message (max 200 chars):" TO WS-MESSAGE
           CALL "WRITE-LINE" USING WS-MESSAGE
           CALL "READ-LONG-LINE" USING WS-CONTENT
           IF END-OF-INPUT
               GOBACK
           END-IF
           IF WS-CONTENT = SPACES
               MOVE "Message cannot be empty." TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               GOBACK
           END-IF
           IF WS-CONTENT(201:50) NOT = SPACES
               MOVE "Message must be 200 characters or fewer."
                   TO WS-MESSAGE
               CALL "WRITE-LINE" USING WS-MESSAGE
               GOBACK
           END-IF

           PERFORM SAVE-MESSAGE
           IF WS-SAVE-OK = 'Y'
               MOVE SPACES TO WS-MESSAGE
               STRING "Message sent to " DELIMITED BY SIZE
                      FUNCTION TRIM(WS-RECIPIENT) DELIMITED BY SIZE
                      " successfully!" DELIMITED BY SIZE
                      INTO WS-MESSAGE
               END-STRING
           ELSE
               MOVE "Message could not be sent. Please try again."
                   TO WS-MESSAGE
           END-IF
           CALL "WRITE-LINE" USING WS-MESSAGE.
           GOBACK.

       VALIDATE-CONNECTION.
           MOVE 'N' TO WS-CONNECTED
           IF WS-FREQ-COUNT > 0
               PERFORM VARYING WS-REQUEST-IDX FROM 1 BY 1
                       UNTIL WS-REQUEST-IDX > WS-FREQ-COUNT
                   IF FUNCTION TRIM(WS-FREQ-STATUS(WS-REQUEST-IDX)) =
                      "ACCEPTED"
                       IF (FUNCTION TRIM(
                              WS-FREQ-SENDER(WS-REQUEST-IDX)) =
                           FUNCTION TRIM(WS-CURRENT-USERNAME)
                           AND FUNCTION TRIM(
                              WS-FREQ-RECEIVER(WS-REQUEST-IDX)) =
                           FUNCTION TRIM(WS-RECIPIENT))
                          OR (FUNCTION TRIM(
                              WS-FREQ-RECEIVER(WS-REQUEST-IDX)) =
                           FUNCTION TRIM(WS-CURRENT-USERNAME)
                           AND FUNCTION TRIM(
                              WS-FREQ-SENDER(WS-REQUEST-IDX)) =
                           FUNCTION TRIM(WS-RECIPIENT))
                           MOVE 'Y' TO WS-CONNECTED
                       END-IF
                   END-IF
               END-PERFORM
           END-IF.

       SAVE-MESSAGE.
           MOVE 'N' TO WS-SAVE-OK
           OPEN EXTEND MESSAGE-FILE
           IF WS-MESSAGE-FILE-STATUS = "35"
               OPEN OUTPUT MESSAGE-FILE
           END-IF
           IF WS-MESSAGE-FILE-STATUS = "00"
               MOVE WS-CURRENT-USERNAME TO MSG-REC-SENDER
               MOVE WS-RECIPIENT TO MSG-REC-RECIPIENT
               MOVE FUNCTION CURRENT-DATE TO MSG-REC-TIMESTAMP
               MOVE WS-CONTENT(1:200) TO MSG-REC-CONTENT
               WRITE MESSAGE-RECORD
               IF WS-MESSAGE-FILE-STATUS = "00"
                   MOVE 'Y' TO WS-SAVE-OK
               END-IF
               CLOSE MESSAGE-FILE
           END-IF.
       END PROGRAM SEND-MESSAGE.
