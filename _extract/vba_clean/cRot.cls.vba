Option Explicit

Private malfap As Double 'pitch en radians
Private malfar As Double 'roll en radians
Dim c1 As Double
Dim s1 As Double
Dim c2 As Double
Dim s2 As Double
Private u1(2, 0) As Double
Private rot1(2, 2) As Double
Private u2(2, 0) As Double
Private rot2(2, 2) As Double
Private utamp() As Variant
Private Pttamp() As Variant
Private Ptdata(2, 0) As Double

Property Get alfap() As Double
' Propriété en lecture
alfap = malfap
End Property
Property Let alfap(alfap As Double)
' Propriété en écriture
malfap = alfap
End Property

Property Get alfar() As Double
' Propriété en lecture
alfar = malfar
End Property
Property Let alfar(alfar As Double)
' Propriété en écriture
malfar = alfar
End Property

Public Sub Pt_Rsol_Rlg(Pt As cPts)

    'rotation autour de y de l'angle alpha pitch autour du point origine du repère
    u1(0, 0) = 0
    u1(1, 0) = 1
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(-malfap)
    s1 = Sin(-malfap)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 1
    u2(1, 0) = 0
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(-malfar)
    s2 = Sin(-malfar)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat
    Ptdata(0, 0) = Pt.RsolX
    Ptdata(1, 0) = Pt.RsolY
    Ptdata(2, 0) = Pt.RsolZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    Pt.RlgX = Pttamp(1, 1)
    Pt.RlgY = Pttamp(2, 1)
    Pt.RlgZ = Pttamp(3, 1)

End Sub

Public Sub Pt_Rlg_Rsol(Pt As cPts)

    'rotation autour de y de l'angle alpha roll autour du point origine du repère
    u1(0, 0) = 1
    u1(1, 0) = 0
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(malfar)
    s1 = Sin(malfar)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 0
    u2(1, 0) = 1
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(malfap)
    s2 = Sin(malfap)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat
    Ptdata(0, 0) = Pt.RlgX
    Ptdata(1, 0) = Pt.RlgY
    Ptdata(2, 0) = Pt.RlgZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    Pt.RsolX = Pttamp(1, 1)
    Pt.RsolY = Pttamp(2, 1)
    Pt.RsolZ = Pttamp(3, 1)

End Sub

Public Sub Tor_Rsol_Rlg(tor As cTorseur)

    'rotation autour de y de l'angle alpha pitch autour du point origine du repère
    u1(0, 0) = 0
    u1(1, 0) = 1
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(-malfap)
    s1 = Sin(-malfap)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 1
    u2(1, 0) = 0
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(-malfar)
    s2 = Sin(-malfar)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat résultantes
    Ptdata(0, 0) = tor.RsolX
    Ptdata(1, 0) = tor.RsolY
    Ptdata(2, 0) = tor.RsolZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    tor.RlgX = Pttamp(1, 1)
    tor.RlgY = Pttamp(2, 1)
    tor.RlgZ = Pttamp(3, 1)

    Erase utamp
    Erase Pttamp

    'Calcul du résultat résultantes
    Ptdata(0, 0) = tor.RsolL
    Ptdata(1, 0) = tor.RsolM
    Ptdata(2, 0) = tor.RsolN

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    tor.RlgL = Pttamp(1, 1)
    tor.RlgM = Pttamp(2, 1)
    tor.RlgN = Pttamp(3, 1)

End Sub

Public Sub Tor_Rlg_Rsol(tor As cTorseur)

    'rotation autour de y de l'angle alpha roll autour du point origine du repère
    u1(0, 0) = 1
    u1(1, 0) = 0
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(-malfar)
    s1 = Sin(-malfar)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 0
    u2(1, 0) = 1
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(malfap)
    s2 = Sin(malfap)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat résultantes
    Ptdata(0, 0) = tor.RlgX
    Ptdata(1, 0) = tor.RlgY
    Ptdata(2, 0) = tor.RlgZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    tor.RsolX = Pttamp(1, 1)
    tor.RsolY = Pttamp(2, 1)
    tor.RsolZ = Pttamp(3, 1)

    Erase utamp
    Erase Pttamp

    'Calcul du résultat résultantes
    Ptdata(0, 0) = tor.RlgL
    Ptdata(1, 0) = tor.RlgM
    Ptdata(2, 0) = tor.RlgN

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    tor.RsolL = Pttamp(1, 1)
    tor.RsolM = Pttamp(2, 1)
    tor.RsolN = Pttamp(3, 1)

End Sub

Public Sub RotSol(Pt As cPts, Angle As Double)

    'rotation autour de y de l'angle alpha pitch autour du point origine du repère
    u1(0, 0) = 0
    u1(1, 0) = 1
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(Angle)
    s1 = Sin(Angle)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'Calcul du résultat
    Ptdata(0, 0) = Pt.RsolX
    Ptdata(1, 0) = Pt.RsolY
    Ptdata(2, 0) = Pt.RsolZ

    Pttamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pt.RsolX = Pttamp(1, 1)
    Pt.RsolY = Pttamp(2, 1)
    Pt.RsolZ = Pttamp(3, 1)

End Sub

Public Sub Pt_RsolNLG_Rlg(Pt As cPts)

    'rotation autour de y de l'angle alpha pitch autour du point origine du repère
    u1(0, 0) = 0
    u1(1, 0) = 1
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(-malfap)
    s1 = Sin(-malfap)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 1
    u2(1, 0) = 0
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(-malfar)
    s2 = Sin(-malfar)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat
    Ptdata(0, 0) = Pt.RsolNLGX
    Ptdata(1, 0) = Pt.RsolNLGY
    Ptdata(2, 0) = Pt.RsolNLGZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    Pt.RlgX = Pttamp(1, 1)
    Pt.RlgY = Pttamp(2, 1)
    Pt.RlgZ = Pttamp(3, 1)

End Sub

Public Sub Pt_Rlg_RsolNLG(Pt As cPts)

    'rotation autour de y de l'angle alpha pitch autour du point origine du repère
    u1(0, 0) = 0
    u1(1, 0) = 1
    u1(2, 0) = 0
    'matrice pour la première rotation
    c1 = Cos(malfap)
    s1 = Sin(malfap)
    rot1(0, 0) = u1(0, 0) ^ 2 * (1 - c1) + c1
    rot1(1, 1) = u1(1, 0) ^ 2 * (1 - c1) + c1
    rot1(2, 2) = u1(2, 0) ^ 2 * (1 - c1) + c1
    rot1(0, 1) = u1(0, 0) * u1(1, 0) * (1 - c1) - u1(2, 0) * s1
    rot1(0, 2) = u1(0, 0) * u1(2, 0) * (1 - c1) + u1(1, 0) * s1
    rot1(1, 0) = u1(0, 0) * u1(1, 0) * (1 - c1) + u1(2, 0) * s1
    rot1(1, 2) = u1(1, 0) * u1(2, 0) * (1 - c1) - u1(0, 0) * s1
    rot1(2, 0) = u1(0, 0) * u1(2, 0) * (1 - c1) - u1(1, 0) * s1
    rot1(2, 1) = u1(1, 0) * u1(2, 0) * (1 - c1) + u1(0, 0) * s1

    'rotation autour du nouveau x de l'angle alpha roll
    u2(0, 0) = 1
    u2(1, 0) = 0
    u2(2, 0) = 0

    utamp = Application.WorksheetFunction.MMult(rot1, u2)
    u2(0, 0) = utamp(1, 1)
    u2(1, 0) = utamp(2, 1)
    u2(2, 0) = utamp(3, 1)
    Erase utamp 'on efface utamp

    'matrice pour la deuxième rotation
    c2 = Cos(malfar)
    s2 = Sin(malfar)
    rot2(0, 0) = u2(0, 0) ^ 2 * (1 - c2) + c2
    rot2(1, 1) = u2(1, 0) ^ 2 * (1 - c2) + c2
    rot2(2, 2) = u2(2, 0) ^ 2 * (1 - c2) + c2
    rot2(0, 1) = u2(0, 0) * u2(1, 0) * (1 - c2) - u2(2, 0) * s2
    rot2(0, 2) = u2(0, 0) * u2(2, 0) * (1 - c2) + u2(1, 0) * s2
    rot2(1, 0) = u2(0, 0) * u2(1, 0) * (1 - c2) + u2(2, 0) * s2
    rot2(1, 2) = u2(1, 0) * u2(2, 0) * (1 - c2) - u2(0, 0) * s2
    rot2(2, 0) = u2(0, 0) * u2(2, 0) * (1 - c2) - u2(1, 0) * s2
    rot2(2, 1) = u2(1, 0) * u2(2, 0) * (1 - c2) + u2(0, 0) * s2

    'Calcul du résultat
    Ptdata(0, 0) = Pt.RlgX
    Ptdata(1, 0) = Pt.RlgY
    Ptdata(2, 0) = Pt.RlgZ

    utamp = Application.WorksheetFunction.MMult(rot1, Ptdata)
    Pttamp = Application.WorksheetFunction.MMult(rot2, utamp)

    Pt.RsolNLGX = Pttamp(1, 1)
    Pt.RsolNLGY = Pttamp(2, 1)
    Pt.RsolNLGZ = Pttamp(3, 1)

End Sub
