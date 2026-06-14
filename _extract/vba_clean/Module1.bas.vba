Function Interpolation(XToFind, ArrayX, ArrayY)
    'Interpolation simple entre 2point
    X = XToFind 'abscisse de l'ordonnée recherchée
    Array1 = ArrayX 'tableau des abscisses
    Array2 = ArrayY 'tableau des ordonnées

    Dim i As Integer
    IndiceXmax = UBound(Array1, 1) 'nombre de valeur dans le tableau
    Xmin = Array1(1, 1)
    Xmax = Array1(IndiceXmax, 1)
    If Array1(1, 1) < Array1(IndiceXmax, 1) Then 'sens des abscisses (croissant ou décroissant)
        Sens = "C" 'Croissant
    Else
        Sens = "D" 'Decroissant
    End If

    If (Sens = "C" And (X < Array1(1, 1) Or X > Array1(IndiceXmax, 1))) Or (Sens = "D" And (X > Array1(1, 1) Or X < Array1(IndiceXmax, 1))) Then
        Interpolation = "La valeur recherchée est en dehors du Tableau"
        GoTo line1
    End If
    i1 = 1
    i2 = 1
    i = 1
    Do While ((i <= IndiceXmax))
        If Array1(i, 1) = X Then
            Test = "i"
            Exit Do
        End If
        If (Sens = "C" And X < Array1(i, 1)) Or (Sens = "D" And X > Array1(i, 1)) Then
                 i1 = i - 1
                 i2 = i
            Exit Do
        End If
        i = i + 1
    Loop

    If Test = "i" Then
       Interpolation = Array2(i, 1) 'l'abscisse existe déjà dans le tableau
    Else
        Interpolation = Array2(i1, 1) + (Array2(i1, 1) - Array2(i2, 1)) * (X - Array1(i1, 1)) / (Array1(i1, 1) - Array1(i2, 1))
    End If
line1:
End Function
