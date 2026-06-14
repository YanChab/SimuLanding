Option Explicit

Dim MLG As New ClMLG
Dim Bal As New cBalancier
Dim H5606 As New ClOil
Dim Pi As Double
Dim ChgtRep As New cRot
Dim PtB As New cPts
Dim PtC As New cPts
Dim PtA As New cPts
Dim PtR As New cPts
Dim TB_sl As New cTorseur
Dim TR_sl As New cTorseur
Dim TR_bal As New cTorseur
Dim TA_bal As New cTorseur
Dim TB_bal As New cTorseur
Dim PtS As New cPts
Dim Tyre As New cTyre
Dim AccMs As New cPts
Dim VitMs As New cPts
Dim DepMs As New cPts
Dim AccMns As New cPts
Dim VitMns As New cPts
Dim DepMns As New cPts
Dim TbCal() As Double
Dim TbCalGaz() As Double
Dim TbCalSum() As Double
Dim NbIt As Double
Dim NbItCal As Double
Dim It As Double
Dim PMs As New cTorseur
Dim Ms As Double
Dim PMns As New cTorseur
Dim Mns As Double
Dim Lift As Double
Dim Vx As Double
Dim NbAffich As Integer
Dim j As Integer
Dim TempsSimu As Double
Dim Vitesse As Double
Dim CoeffAffich As Integer
Dim i As Long
Dim NbLigneBH As Integer
Dim NbLigneTyre As Integer
Dim NbLigneMu As Integer
Dim p As Integer
Dim k As Integer
Dim DEqBh As Double
Dim ReBh As Double
Dim CdBh As Double
Dim DEqBhdet As Double
Dim ReBhdet As Double
Dim CdBhdet As Double
Dim RePis As Double
Dim CdPis As Double
Dim ReDiap As Double
Dim CdDiap As Double
Dim zBR As Double
Dim m As Integer
Dim n As Integer
Dim ZbSolTamp As Double
Dim a As Integer
Dim b As Integer
Dim c As Integer
Dim D As Integer
Dim TbVit As Variant
Dim TbDebutBH() As Double
Dim TbFinBH() As Double
Dim TbProfondeurBH() As Double
Dim NbRainure As Integer
Dim TbBH() As Double
Dim LongueurProgressiviteBH As Double
Dim DiametreRainure As Double

Sub SimuComplete()
Pi = Application.WorksheetFunction.Pi

'Affichage de l'effort gaz
    Worksheets("Summary MLG").Activate
    ActiveSheet.Range("N4:CZ5005").Select
    Selection.Clear

'calcul des loi isothermes
For j = 0 To 2
Sheets("MLG").Cells(24, 3) = Sheets("Summary MLG").Cells(5 + j, 12)

'récupération des données
    Call RecupData
    MLG.Gamma = 1

    ReDim TbCalGaz(MLG.c * 1000, 2)
    For i = 0 To MLG.c * 1000
        TbCalGaz(i, 0) = i
        MLG.D = i / 1000
        MLG.Entraxe = MLG.EntraxeInit - MLG.D
        Call DeterPosBalA
        Call DeterPosBalR
        MLG.v = 0
        MLG.Pgtamp = MLG.Pg
        TbCalGaz(i, 1) = MLG.Pg
        TbCalGaz(i, 2) = MLG.Ftot '-((PtC.RsolX - PtA.RsolX) * (PtA.RsolZ - PtB.RsolZ) / MLG.Entraxe - (PtC.RsolZ - PtA.RsolZ) * (PtA.RsolX - PtB.RsolX) / MLG.Entraxe) / (PtR.RsolX - PtB.RsolX) * MLG.Ftot

    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary MLG").Cells(4 + i, 14 + j * 3) = TbCalGaz(i, 0)
        Sheets("Summary MLG").Cells(4 + i, 15 + j * 3) = TbCalGaz(i, 1) / 100000
        Sheets("Summary MLG").Cells(4 + i, 16 + j * 3) = TbCalGaz(i, 2)
        Sheets("Summary MLG").Cells(32, 3) = TbCalGaz(i, 1) / 100000
    Next

Next

'calcul des loi adiabatiques
For j = 0 To 2
Sheets("MLG").Cells(24, 3) = Sheets("Summary MLG").Cells(5 + j, 12)

'récupération des données
    Call RecupData
    MLG.Gamma = 1.4

    ReDim TbCalGaz(MLG.c * 1000, 2)
    For i = 0 To MLG.c * 1000
        TbCalGaz(i, 0) = i
        MLG.D = i / 1000
        MLG.Entraxe = MLG.EntraxeInit - MLG.D
        Call DeterPosBalA
        Call DeterPosBalR
        MLG.v = 0
        MLG.Pgtamp = MLG.Pg
        TbCalGaz(i, 1) = MLG.Pg
        TbCalGaz(i, 2) = MLG.Ftot '-((PtC.RsolX - PtA.RsolX) * (PtA.RsolZ - PtB.RsolZ) / MLG.Entraxe - (PtC.RsolZ - PtA.RsolZ) * (PtA.RsolX - PtB.RsolX) / MLG.Entraxe) / (PtR.RsolX - PtB.RsolX) * MLG.Ftot

    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary MLG").Cells(4 + i, 23 + j * 3) = TbCalGaz(i, 0)
        Sheets("Summary MLG").Cells(4 + i, 24 + j * 3) = TbCalGaz(i, 1) / 100000
        Sheets("Summary MLG").Cells(4 + i, 25 + j * 3) = TbCalGaz(i, 2)

    Next

Next
If Sheets("MLG").Cells(30, 10) <> "Isotherme" Then
'Simulation de la chute.
'On parcour les 4 cas
For a = 0 To 3

'On copie les information du cas
    Sheets("MLG").Cells(4, 3) = Sheets("Summary MLG").Cells(37, 3 + a * 3)
    Sheets("MLG").Cells(5, 3) = Sheets("Summary MLG").Cells(38, 3 + a * 3)
    Sheets("MLG").Cells(6, 3) = Sheets("Summary MLG").Cells(39, 3 + a * 3)
    Sheets("MLG").Cells(7, 3) = Sheets("Summary MLG").Cells(40, 3 + a * 3)
    Sheets("MLG").Cells(8, 3) = Sheets("Summary MLG").Cells(41, 3 + a * 3)
    Sheets("MLG").Cells(9, 3) = Sheets("Summary MLG").Cells(42, 3 + a * 3)
    Sheets("MLG").Cells(10, 3) = Sheets("Summary MLG").Cells(43, 3 + a * 3)

'Pour chaque cas on fait les 3 températures

    For b = 0 To 2
        Sheets("MLG").Cells(24, 3) = Sheets("Summary MLG").Cells(5 + b, 12)
'On lance le calcul
        Call DropCalcul
'On copie les résultats dans l'onglet summary
        Sheets("Summary MLG").Cells(3 + b * 1003, 33 + a * 18) = "Temps (s)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 34 + a * 18) = "DepMs.RsolZ (m)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 35 + a * 18) = "Tyre.FTyre (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 36 + a * 18) = "TR_sl.RsolX (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 37 + a * 18) = "NLG.d (m)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 38 + a * 18) = "NLG.v (m/s)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 39 + a * 18) = "NLG.Ftot (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 40 + a * 18) = "NLG.Pg (bar)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 41 + a * 18) = "NLG.Pc (bar)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 42 + a * 18) = "NLG.Pd (bar)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 43 + a * 18) = "AccMs.RsolZ (g)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 44 + a * 18) = "TGt_sl.RsolX (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 45 + a * 18) = "TGt_sl.RsolY (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 46 + a * 18) = "TGt_sl.RsolZ (N)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 47 + a * 18) = "TGt_sl.RsolL (N.m)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 48 + a * 18) = "TGt_sl.RsolM (N.m)"
        Sheets("Summary MLG").Cells(3 + b * 1003, 49 + a * 18) = "TGt_sl.RsolN (N.m)"

        For c = 0 To Application.WorksheetFunction.RoundDown(NbItCal / CoeffAffich, 0)
            For D = 0 To 16
                Sheets("Summary MLG").Cells(4 + c + (b) * 1003, 33 + a * 18 + D) = TbCalSum(c * CoeffAffich, D)
            Next
        Next

    Next 'boucle température
Next ' boucle cas
End If
Sheets("MLG").Cells(24, 3) = Sheets("Summary MLG").Cells(5, 12)
Application.Calculation = xlCalculationManual 'Arrête certains calculs automatiques
'Loi hydraulique
'Détente
'If Sheets("MLG").Cells(30, 10) = "Isotherme" Then
'Compression
TbVit = Array(-1, -0.75, -0.5, -0.25, -0.002, 0.002, 0.25, 0.5, 0.75, 1, 1.5, 2, 3)
Sheets("Summary MLG").Cells(3, 107) = "Course en m"
For j = 1 To UBound(TbVit) + 1
    Sheets("Summary MLG").Cells(3, 107 + j) = "Effort " & TbVit(j - 1) & " m/s"
Next

Call CalculBH
MLG.Gamma = 1.4
MLG.Pgtamp = MLG.Pinitbp
For j = 0 To UBound(TbVit)
On Error Resume Next
    ReDim TbCalGaz(MLG.c * 1000, 2)
    Call CalculBH
    If Abs(TbVit(j)) < 0.01 Then
    MLG.Gamma = 1.05
    Else
    MLG.Gamma = 1.4
    End If

    MLG.Pgtamp = MLG.Pinitbp
    For i = 0 To MLG.c * 1000 - 1
        TbCalGaz(i, 0) = i
        MLG.D = i / 1000
        MLG.v = TbVit(j)
        Call CalculHydrau
        MLG.Pgtamp = MLG.Pg
        TbCalGaz(i, 1) = MLG.Pc
        TbCalGaz(i, 2) = MLG.Ftot
        Sheets("Summary MLG").Cells(4 + i, 107) = TbCalGaz(i, 0) / 1000 'course en m
        Sheets("Summary MLG").Cells(4 + i, 108 + j) = -TbCalGaz(i, 2)
    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary MLG").Cells(4 + i, 107) = TbCalGaz(i, 0) / 1000 'course en m
        Sheets("Summary MLG").Cells(4 + i, 108 + j) = -TbCalGaz(i, 2)
   Next
Next
'End If

Sheets("MLG").Cells(24, 3) = Sheets("Summary MLG").Cells(5, 12)
Worksheets("Summary MLG").Activate

Sheets("Summary MLG").Cells(1, 1).Select
Application.Calculation = xlAutomatic 'Réactive les calculs.
End Sub

Sub DropCalcul()
Pi = Application.WorksheetFunction.Pi
Application.Calculation = xlCalculationManual 'Arrête certains calculs automatiques

'récupération des données
Call CalculBH

'Initialisation
NbIt = Application.WorksheetFunction.RoundDown(TempsSimu / It, 0)
CoeffAffich = NbIt / 1000
NbAffich = 60
NbItCal = NbIt
ReDim TbCal(NbIt, NbAffich)
ReDim TbCalSum(NbIt, NbAffich)

'VitMs.RsolZ = -0.3
'ChgtRep.Pt_Rsol_Rlg VitMs
'VitMns.RsolZ = -0.1
'ChgtRep.Pt_Rsol_Rlg VitMns
'Vitesse = Sheets("MLG").Cells(5, 3)
'AccMs.RsolZ = 0
'VitMs.RsolZ = -Vitesse
'ChgtRep.Pt_Rsol_Rlg VitMs
'DepMs.RsolZ = 0
'AccMns.RlgZ = 0
'VitMns.RlgZ = VitMs.RlgZ
'DepMns.RlgZ = 0
'NLG.v = 0
'NLG.d = 0
AccMs.RsolZ = 0
VitMs.RsolZ = -Vitesse
DepMs.RsolZ = 0
MLG.v = 0
MLG.D = 0
Tyre.Accx = 0
Tyre.Vitx = 0
Tyre.Depx = 0

'Stabilisation
For i = 0 To 100000
    MLG.D = MLG.D - 0.00000001
    If Abs(MLG.Ftot) < 1 Then
    Exit For
    End If
Next
'détermination de la position des points R, S et A
MLG.Entraxe = MLG.EntraxeInit - MLG.D
Call DeterPosBalA
Call DeterPosBalR
Bal.ThRY = Atn((PtR.RsolX - PtB.RsolX) / (PtR.RsolZ - PtB.RsolZ))
Bal.ThAY = Atn((PtA.RsolX - PtB.RsolX) / (PtA.RsolZ - PtB.RsolZ))
Tyre.Alpha = 0
Tyre.Omega = 0
'zBR = PtB.RsolZ - PtR.RsolZ

'Itération de calcul

For i = 0 To NbIt
On Error Resume Next
    TbCal(i, 0) = It * i: TbCalSum(i, 0) = TbCal(i, 0)
    AccMs.RsolZ = 1 / Ms * (-TA_bal.RsolZ - TB_bal.RsolZ - PMs.RlgZ): TbCal(i, 1) = AccMs.RsolZ: TbCalSum(i, 10) = AccMs.RsolZ / 9.81
    VitMs.RsolZ = VitMs.RsolZ + AccMs.RsolZ * It: TbCal(i, 2) = VitMs.RsolZ
    DepMs.RsolZ = DepMs.RsolZ + VitMs.RsolZ * It: TbCal(i, 3) = DepMs.RsolZ: TbCalSum(i, 1) = DepMs.RsolZ * 1000
    PtB.RsolZ = PtB.RsolZ + VitMs.RsolZ * It
    PtC.RsolZ = PtC.RsolZ + VitMs.RsolZ * It
    Bal.AlY = 1 / Bal.Jyy * ((PtA.RsolZ - PtB.RsolZ) * TA_bal.RsolX - (PtA.RsolX - PtB.RsolX) * TA_bal.RsolZ + (PtR.RsolZ - PtB.RsolZ) * TR_bal.RsolX - (PtR.RsolX - PtB.RsolX) * TR_bal.RsolZ): TbCal(i, 4) = Bal.AlY
    Bal.OmY = Bal.OmY + Bal.AlY * It: TbCal(i, 5) = Bal.OmY
    Bal.ThAY = Bal.ThAY + Bal.OmY * It: TbCal(i, 6) = Bal.ThAY
    Bal.ThRY = Bal.ThRY + Bal.OmY * It: TbCal(i, 7) = Bal.ThRY
    PtR.RsolX = -Bal.LgRB * Sin(Bal.ThRY) + PtB.RsolX
    PtR.RsolZ = -Bal.LgRB * Cos(Bal.ThRY) + PtB.RsolZ

    Tyre.Defl = Tyre.UnRadius - (PtR.RsolZ - PtS.RsolZ): TbCal(i, 8) = Tyre.Defl: TbCal(i, 9) = Tyre.FTyre: TbCalSum(i, 2) = Tyre.FTyre
    TR_bal.RsolZ = Tyre.FTyre
    'Calcul du Fx
    If Vx <> 0 Then
    Tyre.Slip = (Vx - Tyre.Omega * Tyre.REff) / Abs(Vx): TbCal(i, 26) = Tyre.Slip
    Else
    Tyre.Slip = 0
    End If
    'calcul spin up
    Tyre.FSpin = Tyre.Mu * TR_bal.RsolZ * Sgn(Tyre.Slip): TbCal(i, 45) = Tyre.FSpin
    'Calcul springback
    Tyre.Accx = (-Tyre.Fx + Tyre.FSpin) / Tyre.WheelMass
    Tyre.Vitx = Tyre.Vitx + Tyre.Accx * It: TbCal(i, 46) = Tyre.Vitx
    Tyre.Depx = Tyre.Depx + Tyre.Vitx * It: TbCal(i, 47) = Tyre.Depx

    TR_bal.RsolX = Tyre.Fx: TbCal(i, 24) = TR_bal.RsolX: TbCal(i, 25) = Tyre.Mu: TbCalSum(i, 3) = TR_bal.RsolX
    Tyre.Alpha = (Tyre.FSpin * (Tyre.UnRadius - Tyre.Defl)) / Tyre.j: TbCal(i, 22) = Tyre.Alpha
    Tyre.Omega = Tyre.Omega + Tyre.Alpha * It: TbCal(i, 23) = Tyre.Omega

    PtA.RsolX = -Bal.LgAB * Sin(Bal.ThAY) + PtB.RsolX
    PtA.RsolZ = -Bal.LgAB * Cos(Bal.ThAY) + PtB.RsolZ
    MLG.v = -(((PtC.RsolX - PtA.RsolX) ^ 2 + (PtC.RsolY - PtA.RsolY) ^ 2 + (PtC.RsolZ - PtA.RsolZ) ^ 2) ^ (1 / 2) - MLG.Entraxe) / It: TbCal(i, 10) = MLG.v
    MLG.Entraxe = ((PtC.RsolX - PtA.RsolX) ^ 2 + (PtC.RsolY - PtA.RsolY) ^ 2 + (PtC.RsolZ - PtA.RsolZ) ^ 2) ^ (1 / 2): TbCal(i, 18) = MLG.Entraxe
    MLG.D = MLG.EntraxeInit - MLG.Entraxe: TbCal(i, 11) = MLG.D: TbCalSum(i, 4) = MLG.D * 1000: TbCalSum(i, 5) = MLG.v

    MLG.Pgtamp = MLG.Pg
    If MLG.v <> 0 Then
    Call CalculHydrau
    End If

    TbCal(i, 12) = MLG.Ftot: TbCal(i, 13) = MLG.Fhyd: TbCal(i, 14) = MLG.FFriJoi: TbCal(i, 15) = MLG.FGas: TbCalSum(i, 6) = MLG.Ftot
    TbCal(i, 19) = MLG.SecBh * 1000000
    If MLG.v < -0 And i > 900000 Then
    NbItCal = i
    Exit For
    Else
    NbItCal = NbIt

    End If

    'Calcul effort
    'dans l'amortisseur
    TA_bal.RsolZ = -MLG.Ftot * ((PtC.RsolZ - PtA.RsolZ) / MLG.Entraxe)
    TA_bal.RsolY = 0
    TA_bal.RsolX = -MLG.Ftot * ((PtC.RsolX - PtA.RsolX) / MLG.Entraxe)
    'Dans le pivot du balanceir
     If i = NbIt Then
    TR_bal.RsolX = 0
    TR_bal.RsolY = 7120
    TR_bal.RsolZ = 12320
    TR_bal.RsolL = TR_bal.RsolY * (PtR.RsolZ - PtS.RsolZ)
    TA_bal.RsolX = -((PtR.RsolZ - PtB.RsolZ) * TR_bal.RsolX - (PtR.RsolX - PtB.RsolX) * TR_bal.RsolZ) / ((PtA.RsolZ - PtB.RsolZ) - (PtA.RsolX - PtB.RsolX) * (PtC.RsolZ - PtA.RsolZ) / (PtC.RsolX - PtA.RsolX))
    TA_bal.RsolZ = TA_bal.RsolX * (PtC.RsolZ - PtA.RsolZ) / (PtC.RsolX - PtA.RsolX)
    End If
    TB_bal.RsolX = -TA_bal.RsolX - TR_bal.RsolX
    TB_bal.RsolY = -TA_bal.RsolY - TR_bal.RsolY
    TB_bal.RsolZ = -TA_bal.RsolZ - TR_bal.RsolZ
    TB_bal.RsolL = TR_bal.RsolY * (PtR.RsolZ - PtS.RsolZ) - ((PtA.RsolY - PtB.RsolY) * TA_bal.RsolZ - (PtA.RsolZ - PtB.RsolZ) * TA_bal.RsolY + (PtR.RsolY - PtB.RsolY) * TR_bal.RsolZ - (PtR.RsolZ - PtB.RsolZ) * TR_bal.RsolY)
    TB_bal.RsolM = -((PtA.RsolZ - PtB.RsolZ) * TA_bal.RsolX - (PtA.RsolX - PtB.RsolX) * TA_bal.RsolZ + (PtR.RsolZ - PtB.RsolZ) * TR_bal.RsolX - (PtR.RsolX - PtB.RsolX) * TR_bal.RsolZ)
    TB_bal.RsolN = -((PtA.RsolX - PtB.RsolX) * TA_bal.RsolY - (PtA.RsolY - PtB.RsolY) * TA_bal.RsolX + (PtR.RsolX - PtB.RsolX) * TR_bal.RsolY - (PtR.RsolY - PtB.RsolY) * TR_bal.RsolX)
    TbCal(i, 20) = zBR - (PtB.RsolZ - PtR.RsolZ)
    TbCal(i, 16) = -TA_bal.RsolZ: TbCal(i, 17) = -TA_bal.RsolX
    TbCal(i, 27) = MLG.Pc / 100000: TbCal(i, 28) = MLG.Pd / 100000: TbCal(i, 29) = MLG.Pg / 100000
    TbCalSum(i, 8) = MLG.Pc / 100000: TbCalSum(i, 9) = MLG.Pd / 100000: TbCalSum(i, 7) = MLG.Pg / 100000
    TbCal(i, 30) = MLG.DeltaPc / 100000: TbCal(i, 31) = MLG.DeltaPd / 100000: TbCal(i, 32) = -TB_bal.RsolL: TbCal(i, 33) = -TB_bal.RsolN
    TbCal(i, 34) = Tyre.FTyre: TbCal(i, 35) = TR_bal.RsolX: TbCal(i, 36) = -TA_bal.RsolX / 1000: TbCal(i, 37) = -TA_bal.RsolZ / 1000
    TbCal(i, 38) = -TB_bal.RsolX / 1000: TbCal(i, 39) = -TB_bal.RsolY / 1000: TbCal(i, 40) = -TB_bal.RsolZ / 1000
    TbCal(i, 41) = -TB_bal.RsolL: TbCal(i, 42) = -TB_bal.RsolN
    TbCal(i, 43) = MLG.Pg: TbCal(i, 44) = MLG.Precision

Next

'Calcul de l'effort du ressort gaz
'Call CalculGaz

'Affichage
Call Affichage

Application.Calculation = xlAutomatic 'Réactive les calculs.

End Sub

Sub Affichage()
 Worksheets("Results MLG").Activate
    ActiveSheet.Cells.Select
    Selection.Clear
    Worksheets("MLG").Activate
    ActiveSheet.Cells(1, 1).Select

'0: temps; 1: AccMs.RlgZ; 2: VitMs.RlgZ; 3: DepMs.RlgZ 4: AccMns.RlgZ; 5: VitMns.RlgZ; 6: DepMns.RlgZ
'7: PtR.RlgZ; 8: Tyre.Defl; 9: MLG.v 10: MLG.d 11: MLG.Ftot 12 :MLG.Fhyd 13: Tyre.FTyre 14: MLG.FFriJoi
'15: MLG.FGas 16: MLG.FFriBag 17:PtB.RlgZ 18:PtGb.RlgZ 19:PtGt.RlgZ 20:MLG.XGb 21:MLG.XGt
'22: Tyre.Alpha 22: Tyre.Omega 23: TR_sl.RsolX 24: Tyre.Mu 25: Tyre.Slip 26:PtB.RSolZ
'27 : VGR (TR_sl.RsolZ  28 : Total friction 29: Metering pin Damping factor 30 :Tyre.Omega 31 :AC Vz
'32 : MLG.Pc '33 : MLG.Pg '34 : MLG.DeltaPc
Sheets("Results MLG").Cells(2, 2) = "Temps (s)"
Sheets("Results MLG").Cells(2, 3) = "AccMs.RsolZ (m/s²)"
Sheets("Results MLG").Cells(2, 4) = "VitMs.RsolZ (m/s)"
Sheets("Results MLG").Cells(2, 5) = "DepMs.RsolZ (m)"
Sheets("Results MLG").Cells(2, 6) = "AlY (rad/s²)"
Sheets("Results MLG").Cells(2, 7) = "OmY (rad/s)"
Sheets("Results MLG").Cells(2, 8) = "ThAY (rad)"
Sheets("Results MLG").Cells(2, 9) = "ThRY (rad)"
Sheets("Results MLG").Cells(2, 10) = "Tyre.Defl (m)"
Sheets("Results MLG").Cells(2, 11) = "Tyre.FTyre (N)"
Sheets("Results MLG").Cells(2, 12) = "MLG.v (m/s)"
Sheets("Results MLG").Cells(2, 13) = "MLG.d (m)"
Sheets("Results MLG").Cells(2, 14) = "MLG.Ftot (N)"
Sheets("Results MLG").Cells(2, 15) = "MLG.Fhyd (N)"
Sheets("Results MLG").Cells(2, 16) = "MLG.FFriJoi (N)"
Sheets("Results MLG").Cells(2, 17) = "MLG.FGas (N)"
Sheets("Results MLG").Cells(2, 18) = "TA_bal.RsolZ (N)"
Sheets("Results MLG").Cells(2, 19) = "TA_bal.RsolX (N)"
Sheets("Results MLG").Cells(2, 20) = "MLG.Entraxe (m)"
Sheets("Results MLG").Cells(2, 21) = "Section de la BH (mm²)"
Sheets("Results MLG").Cells(2, 22) = "Course centre roue (m)"
Sheets("Results MLG").Cells(2, 24) = "Tyre.Alpha (rad/s²)"
Sheets("Results MLG").Cells(2, 25) = "Tyre.Omega (rad/s)"
Sheets("Results MLG").Cells(2, 26) = "TR_bal.RsolX (N)"
Sheets("Results MLG").Cells(2, 27) = "Tyre.Mu"
Sheets("Results MLG").Cells(2, 28) = "Tyre.Slip"
Sheets("Results MLG").Cells(2, 29) = "MLG.Pc (bar)"
Sheets("Results MLG").Cells(2, 30) = "MLG.Pd (bar)"
Sheets("Results MLG").Cells(2, 31) = "MLG.Pg (bar)"
Sheets("Results MLG").Cells(2, 32) = "MLG.DeltaPc (bar)"
Sheets("Results MLG").Cells(2, 33) = "MLG.DeltaPd (bar)"
Sheets("Results MLG").Cells(2, 34) = "TB_bal.RsolL (N.m)"
Sheets("Results MLG").Cells(2, 35) = "TB_bal.RsolN (N.m)"
Sheets("Results MLG").Cells(2, 36) = "Reaction sol verticale (N)"
Sheets("Results MLG").Cells(2, 37) = "Reaction sol horizontale (N)"
Sheets("Results MLG").Cells(2, 38) = "Fx Pt C (N)"
Sheets("Results MLG").Cells(2, 39) = "Fz Pt C (N)"
Sheets("Results MLG").Cells(2, 40) = "Fx Pt B (N)"
Sheets("Results MLG").Cells(2, 41) = "Fy Pt B (N)"
Sheets("Results MLG").Cells(2, 42) = "Fz Pt B (N)"
Sheets("Results MLG").Cells(2, 43) = "M/x Pt B (N.m)"
Sheets("Results MLG").Cells(2, 44) = "M/z Pt B (N.m)"
Sheets("Results MLG").Cells(2, 45) = "Pression de gaz"
Sheets("Results MLG").Cells(2, 46) = "Precision"
Sheets("Results MLG").Cells(2, 47) = "Tyre.FSpin"
Sheets("Results MLG").Cells(2, 48) = "Tyre.Vitx"
Sheets("Results MLG").Cells(2, 49) = "Tyre.Depx"

For i = 0 To Application.WorksheetFunction.RoundDown(NbItCal / CoeffAffich, 0)
    For j = 0 To NbAffich
        Sheets("Results MLG").Cells(3 + i, j + 2) = TbCal(i * CoeffAffich, j)
    Next
Next

End Sub

Sub RecupData()

Set MLG = Nothing
MLG.Dp = Sheets("MLG").Cells(35, 11) / 1000 ' conversion en m
MLG.Dbh = Sheets("MLG").Cells(36, 11) / 1000 ' conversion en m
MLG.Dt = Sheets("MLG").Cells(34, 11) / 1000 ' conversion en m
MLG.c = Sheets("MLG").Cells(39, 7) / 1000 ' conversion en m
MLG.Vh = Sheets("MLG").Cells(43, 7) / 1000000 'conversion en m3
MLG.Vgbp = Sheets("MLG").Cells(42, 7) / 1000000 'conversion en m3
MLG.Vginitbp = Sheets("MLG").Cells(42, 7) / 1000000 'conversion en m3
MLG.Pinitbp = Sheets("MLG").Cells(41, 7) * 100000 'conversion en Pa
MLG.Pgtamp = MLG.Pinitbp
MLG.Vghp = Sheets("MLG").Cells(45, 7) / 1000000 'conversion en m3
MLG.Vginithp = Sheets("MLG").Cells(45, 7) / 1000000 'conversion en m3
MLG.Pinithp = Sheets("MLG").Cells(44, 7) * 100000 'conversion en Pa
MLG.Gamma = Sheets("MLG").Cells(46, 7)
'NLG.Pg = NLG.Pinit
'trou de réalim du piston de détente
MLG.DTrouPis = Sheets("MLG").Cells(41, 11) / 1000 ' conversion en m
MLG.NbTrouPis = Sheets("MLG").Cells(42, 11)
MLG.DInsideBh = Sheets("MLG").Cells(37, 11) / 1000 ' conversion en m
MLG.Lbh = Sheets("MLG").Cells(38, 11) / 1000 ' conversion en m
MLG.HauteurPisBh = Sheets("MLG").Cells(43, 11) / 1000 ' conversion en m
MLG.DTrouDiap = Sheets("MLG").Cells(44, 11) / 1000 ' conversion en m
MLG.NbTrouDiap = Sheets("MLG").Cells(45, 11) ' conversion en m
MLG.Dpis = Sheets("MLG").Cells(46, 11) / 1000 ' conversion en m
MLG.OilBulk = Sheets("MLG").Cells(36, 15) * 1000000
MLG.Vtot = (Sheets("MLG").Cells(42, 7) + Sheets("MLG").Cells(43, 7) + Sheets("MLG").Cells(45, 7)) / 1000000 'conversion en m3
'NLG.BagueGuide = Sheets("MLG").Cells(60, 7) / 1000 ' conversion en m
'NLG.BaguePiston = Sheets("MLG").Cells(60, 7) / 1000 ' conversion en m
'NLG.fc = Sheets("MLG").Cells(43, 15) * 1000 ' conversion en N/m
'NLG.ASeal = Sheets("MLG").Cells(42, 15) / 1000 ' conversion en N/m
'NLG.BaguePiston = Sheets("MLG").Cells(60, 7) / 1000 ' conversion en m
H5606.Rho = Sheets("MLG").Cells(37, 15)
H5606.Visc = Sheets("MLG").Cells(35, 15) / 1000000 'conversion en m²/s
H5606.Bulk = Sheets("MLG").Cells(36, 15) * 1000000 'conversion en Pa
H5606.Temp = Sheets("MLG").Cells(34, 15)

'On récupère les infos de la BH
'NbLigneBH = Sheets("MLG").Cells(51, 10).End(xlDown).Row - 48 'on récupère le nombre de ligne du tableau de BH
'Dim tPos() As Double 'vecteur tampon pour la position
'Dim tSec() As Double 'vecteur tampon pour la section
'ReDim tPos(NbLigneBH - 1)
'ReDim tSec(NbLigneBH - 1)
'For i = 0 To NbLigneBH - 1 'on bouble pour remplir les veteur tampon
'tPos(i) = Sheets("MLG").Cells(51 + i, 10) / 1000 'conversion en m
'tSec(i) = Sheets("MLG").Cells(51 + i, 11) / 1000000 'conversion en m²
'Next
'MLG.TabPosBh() = tPos() 'on rempli les vecteurs du MLG
'MLG.TabSecBh() = tSec()

'On récupères les infos du pneu
Tyre.UnRadius = Sheets("MLG").Cells(36, 3) / 1000 'conversion en m
NbLigneTyre = Sheets("MLG").Cells(40, 2).End(xlDown).Row - 39 + 2 'on récupère le nombre de ligne du tableau du pneu on rajoute une valeur en nég et une en +
Dim tDefl() As Double 'vecteur tampon pour la déflection
Dim tLoad() As Double 'vecteur tampon pour l'effort
ReDim tDefl(NbLigneTyre - 1)
ReDim tLoad(NbLigneTyre - 1)
tDefl(0) = -10
tLoad(0) = 0
For i = 1 To NbLigneTyre - 2 'on bouble pour remplir les veteur tampon
tDefl(i) = Sheets("MLG").Cells(39 + i, 2) / 1000 'conversion en m
tLoad(i) = Sheets("MLG").Cells(39 + i, 3) * 1000 'conversion en N
Next
tDefl(NbLigneTyre - 1) = tDefl(NbLigneTyre - 2) + 0.001 '1 mm de plus
tLoad(NbLigneTyre - 1) = tLoad(NbLigneTyre - 2) * 3 'on triple l'effort
Tyre.TabDefl() = tDefl()
Tyre.TabLoad() = tLoad()
'On récupère le muslip ratio
NbLigneMu = Sheets("MLG").Cells(64, 2).End(xlDown).Row - 63  'on récupère le nombre de ligne du tableau du muslip
Dim tMuX() As Double 'vecteur tampon pour la déflection
Dim tMuY() As Double 'vecteur tampon pour l'effort
ReDim tMuX(NbLigneMu - 1)
ReDim tMuY(NbLigneMu - 1)
For i = 0 To NbLigneMu - 1 'on bouble pour remplir les veteur tampon
tMuX(i) = Sheets("MLG").Cells(64 + i, 2)
tMuY(i) = Sheets("MLG").Cells(64 + i, 3)
Next
Tyre.MuSlipX() = tMuX()
Tyre.MuSlipY() = tMuY()
Tyre.j = Sheets("MLG").Cells(35, 7)
'Springback
Tyre.cx = Sheets("MLG").Cells(68, 7)
Tyre.kx = Sheets("MLG").Cells(67, 7)
Tyre.WheelMass = Sheets("MLG").Cells(69, 7)

'On récupère les coordonées des points
'On récupère les coordonées des points dans le repère appareil
PtB.RsolX = Sheets("MLG").Cells(49, 7) / 1000 ' conversion en m
PtB.RsolY = Sheets("MLG").Cells(50, 7) / 1000 ' conversion en m
PtB.RsolZ = Sheets("MLG").Cells(51, 7) / 1000 ' conversion en m
PtA.RsolX = Sheets("MLG").Cells(52, 7) / 1000 ' conversion en m
PtA.RsolY = Sheets("MLG").Cells(53, 7) / 1000 ' conversion en m
PtA.RsolZ = Sheets("MLG").Cells(54, 7) / 1000 ' conversion en m
PtC.RsolX = Sheets("MLG").Cells(55, 7) / 1000 ' conversion en m
PtC.RsolY = Sheets("MLG").Cells(56, 7) / 1000 ' conversion en m
PtC.RsolZ = Sheets("MLG").Cells(57, 7) / 1000 ' conversion en m
PtR.RsolX = Sheets("MLG").Cells(58, 7) / 1000 ' conversion en m
PtR.RsolY = Sheets("MLG").Cells(59, 7) / 1000 ' conversion en m
PtR.RsolZ = Sheets("MLG").Cells(60, 7) / 1000 ' conversion en m
PtS.RsolX = Sheets("MLG").Cells(61, 7) / 1000 ' conversion en m
PtS.RsolY = Sheets("MLG").Cells(62, 7) / 1000 ' conversion en m
PtS.RsolZ = Sheets("MLG").Cells(63, 7) / 1000 ' conversion en m
MLG.EntraxeInit = ((PtC.RsolX - PtA.RsolX) ^ 2 + (PtC.RsolY - PtA.RsolY) ^ 2 + (PtC.RsolZ - PtA.RsolZ) ^ 2) ^ (1 / 2)
Set Bal = Nothing
Bal.LgAB = ((PtB.RsolX - PtA.RsolX) ^ 2 + (PtB.RsolY - PtA.RsolY) ^ 2 + (PtB.RsolZ - PtA.RsolZ) ^ 2) ^ (1 / 2)
Bal.LgRB = ((PtB.RsolX - PtR.RsolX) ^ 2 + (PtB.RsolZ - PtR.RsolZ) ^ 2) ^ (1 / 2)
Bal.LgRA = ((PtA.RsolX - PtR.RsolX) ^ 2 + (PtA.RsolZ - PtR.RsolZ) ^ 2) ^ (1 / 2)
Bal.ThRY = -Atn((PtR.RsolX - PtB.RsolX) / (PtR.RsolZ - PtB.RsolZ))
Bal.ThAY = -Atn((PtA.RsolX - PtB.RsolX) / (PtA.RsolZ - PtB.RsolZ))

ChgtRep.alfar = Sheets("MLG").Cells(37, 7) * 2 * Pi / 360
ChgtRep.alfap = Sheets("MLG").Cells(8, 3) * 2 * Pi / 360
ChgtRep.Pt_Rsol_Rlg PtA
ChgtRep.Pt_Rsol_Rlg PtC
ChgtRep.Pt_Rsol_Rlg PtR
PtA.RsolX = PtA.RlgX
PtA.RsolY = PtA.RlgY
PtA.RsolZ = PtA.RlgZ
PtC.RsolX = PtC.RlgX
PtC.RsolY = PtC.RlgY
PtC.RsolZ = PtC.RlgZ
PtR.RsolX = PtR.RlgX
PtR.RsolY = PtR.RlgY
PtR.RsolZ = PtR.RlgZ
PtS.RsolX = PtR.RlgX
PtS.RsolY = PtR.RlgY
PtS.RsolZ = PtR.RlgZ - Tyre.UnRadius

'On récupère les masse et torseur des poids
Lift = Sheets("MLG").Cells(7, 3)
Ms = Sheets("MLG").Cells(4, 3)
PMs.RsolZ = Ms * 9.81 * (1 - Lift) 'conversion en N
ChgtRep.Tor_Rsol_Rlg PMs
Mns = Sheets("MLG").Cells(34, 7)
PMns.RsolZ = Mns * 9.81  'conversion en N
ChgtRep.Tor_Rsol_Rlg PMns
Vx = Sheets("MLG").Cells(6, 3)
Bal.Jyy = Sheets("MLG").Cells(64, 7)
Vitesse = Sheets("MLG").Cells(5, 3)
TempsSimu = Sheets("MLG").Cells(9, 3)
It = Sheets("MLG").Cells(10, 3)

Set TR_bal = New cTorseur
Set TA_bal = New cTorseur
Set TB_bal = New cTorseur

End Sub

Sub CalculHydrau()
'pour la compressibilité
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: PC, 1: Qc,
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double
Dim i As Integer
Dim k As Integer
Dim j As Integer

'Calcul du Cd de la BH
MLG.Qc = MLG.Sc * MLG.v

DEqBh = Sqr(Pi * MLG.SecBh / 4)
ReBh = (Abs(MLG.Qc) * DEqBh / (MLG.SecBh)) / H5606.Visc

If ReBh * DEqBh / 0.003 < 50 Then
CdBh = (2.28 + 64 * 0.003 / (ReBh * DEqBh)) ^ (-1 / 2)
Else
CdBh = (1.5 + 13.74 * (0.003 / (ReBh * DEqBh)) ^ (1 / 2)) ^ (-1 / 2)
End If

DEqBhdet = Sqr(Pi * MLG.SecBh / 4)
ReBhdet = (Abs(MLG.Qc) * DEqBhdet / (MLG.SecBh)) / H5606.Visc
If ReBhdet * DEqBhdet / 0.003 < 50 Then
    CdBhdet = (2.28 + 64 * 0.003 / (ReBhdet * DEqBhdet)) ^ (-1 / 2)
Else
    CdBhdet = (1.5 + 13.74 * (0.003 / (ReBhdet * DEqBhdet)) ^ (1 / 2)) ^ (-1 / 2)
End If

If MLG.Qc > 0 Then
    'MLG.DeltaPc = 1 / 2 * H5606.Rho * (MLG.Qc / (MLG.SecBh * CdBh)) ^ 2 * Sgn(MLG.Qc)
    'Test de l'intégration de la compressibilité de l'huile
    xRes(0) = MLG.Pc
    xRes(1) = MLG.Qc

    For i = 0 To 3
        f(0) = xRes(1) - MLG.Sc * MLG.v + MLG.Sc * (MLG.c - MLG.D) / H5606.Bulk * (xRes(0) - MLG.Pc) / It
        f(1) = (xRes(0) - MLG.Pg) - 1 / 2 * H5606.Rho * (xRes(1) / (MLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))
        'mPrecision  = f(0) + f(1)
        df(0, 0) = MLG.Sc * (MLG.c - MLG.D) / (H5606.Bulk * It): df(0, 1) = 1
        df(1, 0) = 1: df(1, 1) = -xRes(1) * H5606.Rho * (1 / (MLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))

        'inversion de la matrice
        det = Application.WorksheetFunction.MDeterm(df)

        If det = 0 Then
            MsgBox ("le déterminant est nul")
            Else
            invdf = Application.WorksheetFunction.MInverse(df)
        End If

        'Calcul des inconnues:
        For k = 0 To neq
            For j = 0 To neq
                xRes(k) = xRes(k) - invdf(k + 1, j + 1) * f(j)
            Next
        Next

        MLG.DeltaPc = xRes(0) - MLG.Pg
        MLG.Qc = xRes(1)
    Next

Else

   MLG.DeltaPc = 1 / 2 * H5606.Rho * (MLG.Qc / (MLG.SecBh * CdBhdet)) ^ 2 * Sgn(MLG.Qc)
End If
'MLG.DeltaPbh = 128 * H5606.Rho * H5606.Visc * MLG.Lbh / (Pi * MLG.DInsideBh ^ 4) * MLG.Qc

RePis = (Abs(MLG.Qd) * MLG.DTrouPis / (MLG.STrouPis)) / H5606.Visc
If RePis * MLG.DTrouPis / MLG.HauteurPisBh < 50 Then
CdPis = (2.28 + 64 * MLG.HauteurPisBh / (RePis * MLG.DTrouPis)) ^ (-1 / 2)
Else
CdPis = (1.5 + 13.74 * (MLG.HauteurPisBh / (RePis * MLG.DTrouPis)) ^ (1 / 2)) ^ (-1 / 2)
End If
ReDiap = (Abs(MLG.Qd) * MLG.DTrouDiap / (MLG.STrouDiap)) / H5606.Visc
If ReDiap * MLG.DTrouDiap / 0.001 < 50 Then
CdDiap = (2.28 + 64 * 0.001 / (ReDiap * MLG.DTrouDiap)) ^ (-1 / 2)
Else
CdDiap = (1.5 + 13.74 * (0.001 / (ReDiap * MLG.DTrouDiap)) ^ (1 / 2)) ^ (-1 / 2)
End If

If MLG.Qd < 0 Then
    MLG.DeltaPd = 1 / 2 * H5606.Rho * (MLG.Qd / (MLG.STrouDiap * CdDiap)) ^ 2 * Sgn(MLG.Qd) + 1 / 2 * H5606.Rho * (MLG.Qd / (MLG.STrouPis * CdPis)) ^ 2 * Sgn(MLG.Qd)
Else
   MLG.DeltaPd = 1 / 2 * H5606.Rho * (MLG.Qd / (MLG.STrouPis * CdPis)) ^ 2 * Sgn(MLG.Qd)
End If

Exit Sub
eh:
    MsgBox Err.Description & Err.HelpContext

End Sub

Sub DeterPosBalA()

'On résoud le système pour calculer la perte de charge et les débits.
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: DeltaPc, 1: Qbh, 2: Qp
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double

xRes(0) = PtA.RsolX
xRes(1) = PtA.RsolZ

For p = 0 To 5
f(0) = MLG.Entraxe ^ 2 - (PtC.RsolX - xRes(0)) ^ 2 - (PtC.RsolZ - xRes(1)) ^ 2
f(1) = Bal.LgAB ^ 2 - (PtB.RsolX - xRes(0)) ^ 2 - (PtB.RsolZ - xRes(1)) ^ 2

df(0, 0) = 2 * PtC.RsolX - 2 * xRes(0): df(0, 1) = 2 * PtC.RsolZ - 2 * xRes(1)
df(1, 0) = 2 * PtB.RsolX - 2 * xRes(0): df(1, 1) = 2 * PtB.RsolZ - 2 * xRes(1)

'inversion de la matrice
det = Application.WorksheetFunction.MDeterm(df)

If det = 0 Then
    MsgBox ("le déterminant est nul")
    Else
    invdf = Application.WorksheetFunction.MInverse(df)
End If

'Calcul des inconnues:
    For k = 0 To neq
        For n = 0 To neq
            xRes(k) = xRes(k) - invdf(k + 1, n + 1) * f(n)
        Next
    Next

Next

PtA.RsolX = xRes(0)
PtA.RsolZ = xRes(1)

End Sub

Sub DeterPosBalR()

'On résoud le système pour calculer la perte de charge et les débits.
Dim neq As Integer
neq = 1
Dim xRes() As Double
ReDim xRes(neq) '0: DeltaPc, 1: Qbh, 2: Qp
Dim f() As Double
ReDim f(neq)
Dim df() As Double
ReDim df(neq, neq)
Dim invdf() As Variant
Dim det As Double

xRes(0) = PtR.RsolX
xRes(1) = PtR.RsolZ

For p = 0 To 5
f(0) = Bal.LgRA ^ 2 - (PtA.RsolX - xRes(0)) ^ 2 - (PtA.RsolZ - xRes(1)) ^ 2
f(1) = Bal.LgRB ^ 2 - (PtB.RsolX - xRes(0)) ^ 2 - (PtB.RsolZ - xRes(1)) ^ 2

df(0, 0) = 2 * PtA.RsolX - 2 * xRes(0): df(0, 1) = 2 * PtA.RsolZ - 2 * xRes(1)
df(1, 0) = 2 * PtB.RsolX - 2 * xRes(0): df(1, 1) = 2 * PtB.RsolZ - 2 * xRes(1)

'inversion de la matrice
det = Application.WorksheetFunction.MDeterm(df)

If det = 0 Then
    MsgBox ("le déterminant est nul")
    Else
    invdf = Application.WorksheetFunction.MInverse(df)
End If

'Calcul des inconnues:
    For k = 0 To neq
        For n = 0 To neq
            xRes(k) = xRes(k) - invdf(k + 1, n + 1) * f(n)
        Next
    Next

Next

PtR.RsolX = xRes(0)
PtR.RsolZ = xRes(1)

End Sub

Sub CalculBH()
Dim r1 As Double
Dim r2 As Double
Dim e As Double

'On récupère les données
Call RecupData
DiametreRainure = Sheets("MLG").Cells(49, 14)
r1 = MLG.Dbh / 2 * 1000
r2 = DiametreRainure / 2
NbRainure = Sheets("MLG").Cells(47, 16).End(xlToRight)
'Tableau position début
'Tableau position fin
'Tableau profondeur
ReDim TbDebutBH(NbRainure)
ReDim TbFinBH(NbRainure)
ReDim TbProfondeurBH(NbRainure)
For k = 0 To NbRainure - 1
    TbDebutBH(k) = Sheets("MLG").Cells(48, 16 + k)
    TbFinBH(k) = Sheets("MLG").Cells(49, 16 + k)
    TbProfondeurBH(k) = Sheets("MLG").Cells(50, 16 + k)
Next

'On nettoie le tableau existant
    Worksheets("MLG").Activate
    ActiveSheet.Range("J51:K551").Select
    Selection.Clear

'On calcul la section tous les mm jusqu'à la fin de course
ReDim TbBH(MLG.c * 1000, NbRainure - 1)
For k = 0 To NbRainure - 1
    'Calcul progressivité
    LongueurProgressiviteBH = Int((r2 ^ 2 - (r2 - (r1 - TbProfondeurBH(k))) ^ 2) ^ (1 / 2))
    For m = 0 To MLG.c * 1000
        e = TbProfondeurBH(k) + r2
        If m >= TbDebutBH(k) And m <= TbFinBH(k) Then
            TbBH(m, k) = r1 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r1 ^ 2 - r2 ^ 2) / (2 * e * r1)) + r2 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r2 ^ 2 - r1 ^ 2) / (2 * e * r2)) - 1 / 2 * ((-e + r1 + r2) * (e + r1 - r2) * (e - r1 + r2) * (e + r1 + r2)) ^ (1 / 2)
        ElseIf m >= TbDebutBH(k) - LongueurProgressiviteBH And m < TbDebutBH(k) Then
            TbBH(m, k) = ((LongueurProgressiviteBH - (TbDebutBH(k) - m)) / LongueurProgressiviteBH) * (r1 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r1 ^ 2 - r2 ^ 2) / (2 * e * r1)) + r2 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r2 ^ 2 - r1 ^ 2) / (2 * e * r2)) - 1 / 2 * ((-e + r1 + r2) * (e + r1 - r2) * (e - r1 + r2) * (e + r1 + r2)) ^ (1 / 2))
        ElseIf m > TbFinBH(k) And m < TbFinBH(k) + LongueurProgressiviteBH Then
            TbBH(m, k) = ((LongueurProgressiviteBH - (m - TbFinBH(k))) / LongueurProgressiviteBH) * (r1 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r1 ^ 2 - r2 ^ 2) / (2 * e * r1)) + r2 ^ 2 * WorksheetFunction.Acos((e ^ 2 + r2 ^ 2 - r1 ^ 2) / (2 * e * r2)) - 1 / 2 * ((-e + r1 + r2) * (e + r1 - r2) * (e - r1 + r2) * (e + r1 + r2)) ^ (1 / 2))
        Else
            TbBH(m, k) = 0
        End If
    Next
Next

'On fait la somme des section des 8 rainures
For m = 0 To MLG.c * 1000
    Sheets("MLG").Cells(51 + m, 10) = m
    For k = 0 To NbRainure - 1
        Sheets("MLG").Cells(51 + m, 11) = Sheets("MLG").Cells(51 + m, 11) + TbBH(m, k)
    Next
Next

'On récupère les infos de la BH
NbLigneBH = Sheets("MLG").Cells(51, 10).End(xlDown).Row - 48 'on récupère le nombre de ligne du tableau de BH
Dim tPos() As Double 'vecteur tampon pour la position
Dim tSec() As Double 'vecteur tampon pour la section
ReDim tPos(NbLigneBH - 1)
ReDim tSec(NbLigneBH - 1)
For k = 0 To NbLigneBH - 1 'on bouble pour remplir les veteur tampon
tPos(k) = Sheets("MLG").Cells(51 + k, 10) / 1000 - Sheets("MLG").Cells(51 + k, 11) / 2000 'conversion en m
tSec(k) = Sheets("MLG").Cells(51 + k, 11) / 1000000 'conversion en m²
Next
MLG.TabPosBh() = tPos() 'on rempli les vecteurs du MLG
MLG.TabSecBh() = tSec()

End Sub
