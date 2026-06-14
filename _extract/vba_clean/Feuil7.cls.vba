Sub ExporterVersCSV()
    Dim ws As Worksheet
    Dim rng As Range
    Dim ligne As Range
    Dim cellule As Range
    Dim cheminFichier As String
    Dim contenuLigne As String
    Dim fichierNum As Integer

    ' Référence à la feuille active
    Set ws = ActiveSheet
    Set rng = Range("DC3:DO324")

    ' Demande à l'utilisateur où sauvegarder le fichier
    cheminFichier = Application.GetSaveAsFilename( _
        InitialFileName:=ws.Name & ".csv", _
        FileFilter:="Fichiers CSV (*.csv), *.csv")

    If cheminFichier = "False" Then Exit Sub ' Annulation

    ' Ouvre le fichier en écriture
    fichierNum = FreeFile
    Open cheminFichier For Output As #fichierNum

    ' Parcours des lignes et cellules
    For Each ligne In rng.Rows
        contenuLigne = ""
        For Each cellule In ligne.Cells
            contenuLigne = contenuLigne & """" & cellule.Text & """" & "," ' Ajoute des guillemets
        Next cellule
        contenuLigne = Left(contenuLigne, Len(contenuLigne) - 1) ' Supprime la dernière virgule
        Print #fichierNum, contenuLigne
    Next ligne

    Close #fichierNum
    MsgBox "Export terminé vers : " & cheminFichier
End Sub
