Sub RunSQLQueryAndPasteResults()

    Dim conn As Object
    Dim rs As Object
    Dim query As String
    Dim lastRow As Long
    Dim row As Long
    Dim col As Long
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Sheet1") ' Adjust if your sheet has a different name

    ' Combine SQL query from B1 and B2
    query = ws.Range("B1").Value & " " & ws.Range("B2").Value

    ' Create a new ADODB connection
    Set conn = CreateObject("ADODB.Connection")
    Set rs = CreateObject("ADODB.Recordset")
    
    ' Replace with your connection string
    conn.ConnectionString = "YourConnectionStringHere"
    conn.Open
    
    ' Execute the query
    rs.Open query, conn

    ' Find the last row in Column I
    lastRow = ws.Cells(ws.Rows.Count, "I").End(xlUp).Row + 1
    
    ' Loop through the recordset and paste data starting from lastRow in column I
    row = lastRow
    col = 9 ' Column I (9th column)
    
    Do Until rs.EOF
        For i = 0 To rs.Fields.Count - 1
            ws.Cells(row, col + i).Value = rs.Fields(i).Value
        Next i
        row = row + 1
        rs.MoveNext
    Loop

    ' Clean up
    rs.Close
    conn.Close
    Set rs = Nothing
    Set conn = Nothing

End Sub