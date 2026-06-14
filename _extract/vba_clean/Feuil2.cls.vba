Option Explicit

Dim NLG As New ClNLG
Dim H5606 As New ClOil
Dim Pi As Double
Dim ChgtRep As New cRot
Dim PtB As New cPts
Dim PtGt As New cPts
Dim PtGb As New cPts
Dim PtR As New cPts
Dim TR_sl As New cTorseur
Dim TB_sl As New cTorseur
Dim TGt_sl As New cTorseur
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
    Worksheets("Summary NLG").Activate
    ActiveSheet.Range("N4:CZ5005").Select
    Selection.Clear

'calcul des loi isothermes
For j = 0 To 2
Sheets("NLG").Cells(24, 3) = Sheets("Summary NLG").Cells(5 + j, 12)

'récupération des données
    Call RecupData
    NLG.Gamma = 1

    ReDim TbCalGaz(NLG.c * 1000, 2)
    For i = 0 To NLG.c * 1000
        TbCalGaz(i, 0) = i
        NLG.D = i / 1000
        NLG.v = 0
        NLG.Pgtamp = NLG.Pg
        TbCalGaz(i, 1) = NLG.Pg
        TbCalGaz(i, 2) = NLG.Ftot
    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary NLG").Cells(4 + i, 14 + j * 3) = TbCalGaz(i, 0)
        Sheets("Summary NLG").Cells(4 + i, 15 + j * 3) = TbCalGaz(i, 1) / 100000
        Sheets("Summary NLG").Cells(4 + i, 16 + j * 3) = TbCalGaz(i, 2)
        Sheets("Summary NLG").Cells(32, 3) = TbCalGaz(i, 1) / 100000
    Next

Next

'calcul des loi adiabatiques
For j = 0 To 2
Sheets("NLG").Cells(24, 3) = Sheets("Summary NLG").Cells(5 + j, 12)

'récupération des données
    Call RecupData
    NLG.Gamma = 1.4

    ReDim TbCalGaz(NLG.c * 1000, 2)
    For i = 0 To NLG.c * 1000
        TbCalGaz(i, 0) = i
        NLG.D = i / 1000
        NLG.v = 0
        NLG.Pgtamp = NLG.Pg
        TbCalGaz(i, 1) = NLG.Pg
        TbCalGaz(i, 2) = NLG.Ftot
    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary NLG").Cells(4 + i, 23 + j * 3) = TbCalGaz(i, 0)
        Sheets("Summary NLG").Cells(4 + i, 24 + j * 3) = TbCalGaz(i, 1) / 100000
        Sheets("Summary NLG").Cells(4 + i, 25 + j * 3) = TbCalGaz(i, 2)

    Next

Next

If Sheets("NLG").Cells(30, 10) <> "Isotherme" Then

'Simulation de la chute.
'On parcour les 4 cas
For a = 0 To 3

'On copie les information du cas
    Sheets("NLG").Cells(4, 3) = Sheets("Summary NLG").Cells(37, 3 + a * 3)
    Sheets("NLG").Cells(5, 3) = Sheets("Summary NLG").Cells(38, 3 + a * 3)
    Sheets("NLG").Cells(6, 3) = Sheets("Summary NLG").Cells(39, 3 + a * 3)
    Sheets("NLG").Cells(7, 3) = Sheets("Summary NLG").Cells(40, 3 + a * 3)
    Sheets("NLG").Cells(8, 3) = Sheets("Summary NLG").Cells(41, 3 + a * 3)
    Sheets("NLG").Cells(9, 3) = Sheets("Summary NLG").Cells(42, 3 + a * 3)
    Sheets("NLG").Cells(10, 3) = Sheets("Summary NLG").Cells(43, 3 + a * 3)

'Pour chaque cas on fait les 3 températures

    For b = 0 To 2
        Sheets("NLG").Cells(24, 3) = Sheets("Summary NLG").Cells(5 + b, 12)
'On lance le calcul
        Call DropCalcul
'On copie les résultats dans l'onglet summary
        Sheets("Summary NLG").Cells(3 + b * 1003, 33 + a * 18) = "Temps (s)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 34 + a * 18) = "DepMs.RsolZ (m)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 35 + a * 18) = "Tyre.FTyre (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 36 + a * 18) = "TR_sl.RsolX (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 37 + a * 18) = "NLG.d (m)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 38 + a * 18) = "NLG.v (m/s)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 39 + a * 18) = "NLG.Ftot (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 40 + a * 18) = "NLG.Pg (bar)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 41 + a * 18) = "NLG.Pc (bar)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 42 + a * 18) = "NLG.Pd (bar)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 43 + a * 18) = "AccMs.RsolZ (g)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 44 + a * 18) = "TGt_sl.RsolX (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 45 + a * 18) = "TGt_sl.RsolY (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 46 + a * 18) = "TGt_sl.RsolZ (N)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 47 + a * 18) = "TGt_sl.RsolL (N.m)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 48 + a * 18) = "TGt_sl.RsolM (N.m)"
        Sheets("Summary NLG").Cells(3 + b * 1003, 49 + a * 18) = "TGt_sl.RsolN (N.m)"

        For c = 0 To Application.WorksheetFunction.RoundDown(NbItCal / CoeffAffich, 0)
            For D = 0 To 16
                Sheets("Summary NLG").Cells(4 + c + (b) * 1003, 33 + a * 18 + D) = TbCalSum(c * CoeffAffich, D)
            Next
        Next

    Next 'boucle température
Next ' boucle cas
End If
Sheets("NLG").Cells(24, 3) = Sheets("Summary NLG").Cells(5, 12)
'Application.Calculation = xlCalculationManual 'Arrête certains calculs automatiques
'Loi hydraulique
'Détente

'Compression
TbVit = Array(-1, -0.75, -0.5, -0.25, -0.002, 0.002, 0.25, 0.5, 0.75, 1, 1.5, 2, 3)
Sheets("Summary NLG").Cells(3, 107) = "Course en m"
For j = 1 To UBound(TbVit) + 1
    Sheets("Summary NLG").Cells(3, 107 + j) = "Effort " & TbVit(j - 1) & " m/s"
Next

Call CalculBH
NLG.Gamma = 1.4
NLG.Pgtamp = NLG.Pinitbp
For j = 0 To UBound(TbVit)
    ReDim TbCalGaz(NLG.c * 1000, 2)
    Call CalculBH
    If Abs(TbVit(j)) < 0.01 Then
    NLG.Gamma = 1.05
    Else
    NLG.Gamma = 1.4
    End If

    NLG.Pgtamp = NLG.Pinitbp
    For i = 0 To NLG.c * 1000
     On Error Resume Next
        TbCalGaz(i, 0) = i
        NLG.D = i / 1000
        NLG.v = TbVit(j)
        Call CalculHydrau
        NLG.Pgtamp = NLG.Pg
        TbCalGaz(i, 1) = NLG.Pc
        TbCalGaz(i, 2) = NLG.Ftot
        Sheets("Summary NLG").Cells(4 + i, 107) = TbCalGaz(i, 0) / 1000 'course en m
        Sheets("Summary NLG").Cells(4 + i, 108 + j) = -TbCalGaz(i, 2)
    Next

    For i = 0 To UBound(TbCalGaz, 1)
        Sheets("Summary NLG").Cells(4 + i, 107) = TbCalGaz(i, 0) / 1000 'course en m
        Sheets("Summary NLG").Cells(4 + i, 108 + j) = -TbCalGaz(i, 2)
    Next
Next

Sheets("NLG").Cells(24, 3) = Sheets("Summary NLG").Cells(5, 12)
Worksheets("Summary NLG").Activate

Sheets("Summary NLG").Cells(1, 1).Select
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
VitMs.RsolZ = -0.3
ChgtRep.Pt_Rsol_Rlg VitMs
VitMns.RsolZ = -0.1
ChgtRep.Pt_Rsol_Rlg VitMns
Vitesse = Sheets("NLG").Cells(5, 3)
AccMs.RsolZ = 0
VitMs.RsolZ = -Vitesse
ChgtRep.Pt_Rsol_Rlg VitMs
DepMs.RsolZ = 0
AccMns.RlgZ = 0
VitMns.RlgZ = VitMs.RlgZ
DepMns.RlgZ = 0
NLG.v = 0
NLG.D = 0
Tyre.Accx = 0
Tyre.Vitx = 0
Tyre.Depx = 0
'Stabilisation
For i = 0 To 100000
    NLG.D = NLG.D - 0.00000001
    If Abs(NLG.Ftot) < 1 Then
    Exit For
    End If
Next
PtB.RlgZ = PtB.RlgZ - NLG.D
ChgtRep.Pt_Rlg_Rsol PtB
PtGb.RlgZ = PtGb.RlgZ - NLG.D
ChgtRep.Pt_Rlg_Rsol PtGb
Tyre.Alpha = 0
Tyre.Omega = 0
TB_sl.RlgZ = NLG.Ftot
ChgtRep.Tor_Rlg_Rsol TB_sl

'Itération de calcul

For i = 0 To NbIt

    TbCal(i, 0) = It * i: TbCalSum(i, 0) = TbCal(i, 0)
    AccMs.RsolZ = 1 / Ms * (TB_sl.RsolZ - PMs.RsolZ): TbCal(i, 1) = AccMs.RsolZ: TbCalSum(i, 10) = AccMs.RsolZ / 9.81
    VitMs.RsolZ = VitMs.RsolZ + AccMs.RsolZ * It: TbCal(i, 2) = VitMs.RsolZ
    DepMs.RsolZ = DepMs.RsolZ + VitMs.RsolZ * It: TbCal(i, 3) = DepMs.RsolZ: TbCalSum(i, 1) = DepMs.RsolZ * 1000
    ChgtRep.Pt_Rsol_Rlg VitMs
    'AccMs.RlgZ = 1 / Ms * (NLG.Ftot - PMs.RlgZ): TbCal(i, 1) = AccMs.RlgZ
    'VitMs.RlgZ = VitMs.RlgZ + AccMs.RlgZ * It: TbCal(i, 2) = VitMs.RlgZ
    'DepMs.RlgZ = DepMs.RlgZ + VitMs.RlgZ * It: TbCal(i, 3) = DepMs.RlgZ
    AccMns.RlgZ = 1 / Mns * (-NLG.Ftot + TR_sl.RlgZ): TbCal(i, 4) = AccMns.RlgZ
    VitMns.RlgZ = VitMns.RlgZ + AccMns.RlgZ * It: TbCal(i, 5) = VitMns.RlgZ
    DepMns.RlgZ = DepMns.RlgZ + VitMns.RlgZ * It: TbCal(i, 6) = DepMns.RlgZ
    PtR.RlgZ = PtR.RlgZ + VitMns.RlgZ * It: TbCal(i, 7) = PtR.RlgZ
    ChgtRep.Pt_Rlg_Rsol PtR
    Tyre.Defl = Tyre.UnRadius - (PtR.RsolZ - PtS.RsolZ): TbCal(i, 8) = Tyre.Defl: TbCal(i, 13) = Tyre.FTyre: TbCalSum(i, 2) = Tyre.FTyre
    TR_sl.RsolZ = Tyre.FTyre
    'Calcul du Fx
    If Vx <> 0 Then
    Tyre.Slip = (Vx - Tyre.Omega * Tyre.REff) / Abs(Vx): TbCal(i, 26) = Tyre.Slip
    Else
    Tyre.Slip = 0
    End If
    'calcul spin up
    Tyre.FSpin = Tyre.Mu * TR_sl.RsolZ * Sgn(Tyre.Slip): TbCal(i, 45) = Tyre.FSpin
    'Calcul springback
    Tyre.Accx = (-Tyre.Fx + Tyre.FSpin) / Tyre.WheelMass
    Tyre.Vitx = Tyre.Vitx + Tyre.Accx * It: TbCal(i, 46) = Tyre.Vitx
    Tyre.Depx = Tyre.Depx + Tyre.Vitx * It: TbCal(i, 47) = Tyre.Depx

    TR_sl.RsolX = Tyre.Fx: TbCal(i, 24) = TR_sl.RsolX: TbCal(i, 25) = Tyre.Mu: TbCalSum(i, 3) = TR_sl.RsolX
    Tyre.Alpha = (Tyre.FSpin * (Tyre.UnRadius - Tyre.Defl)) / Tyre.j: TbCal(i, 22) = Tyre.Alpha
    Tyre.Omega = Tyre.Omega + Tyre.Alpha * It: TbCal(i, 23) = Tyre.Omega
    ChgtRep.Tor_Rsol_Rlg TR_sl: TbCal(i, 27) = TR_sl.RlgX

    'Calcul effort amortissement
    NLG.v = -(VitMs.RlgZ - VitMns.RlgZ): TbCal(i, 9) = NLG.v
    NLG.D = NLG.D + NLG.v * It: TbCal(i, 10) = NLG.D
    NLG.Pgtamp = NLG.Pg
    Call CalculHydrau
    TB_sl.RlgX = TR_sl.RlgX
    TB_sl.RlgZ = NLG.Ftot
    'TB_sl.RsolZ = TB_sl.RlgZ / Cos(ChgtRep.alfap)
    ChgtRep.Tor_Rlg_Rsol TB_sl
    TbCal(i, 11) = NLG.Ftot: TbCal(i, 12) = NLG.Fhyd: TbCal(i, 14) = NLG.FFriJoi: TbCal(i, 15) = NLG.FGas
    TbCalSum(i, 4) = NLG.D * 1000: TbCalSum(i, 5) = NLG.v: TbCalSum(i, 6) = NLG.Ftot: TbCalSum(i, 7) = NLG.Pg / 100000: TbCalSum(i, 8) = NLG.Pc / 100000: TbCalSum(i, 9) = NLG.Pd / 100000

    'points
    ZbSolTamp = PtB.RsolZ
    PtB.RlgZ = PtB.RlgZ + VitMs.RlgZ * It: TbCal(i, 17) = NLG.SecBh * 1000000
    PtGb.RlgZ = PtGb.RlgZ + VitMs.RlgZ * It: TbCal(i, 18) = PtGb.RlgZ
    PtGt.RlgZ = PtGt.RlgZ + VitMns.RlgZ * It: TbCal(i, 19) = PtGt.RlgZ
    ChgtRep.Pt_Rlg_Rsol PtGb
    ChgtRep.Pt_Rlg_Rsol PtGt
    ChgtRep.Pt_Rlg_Rsol PtB
    If i = NbIt Then
        TR_sl.RsolX = 0
        'TR_sl.RsolY = 2290
        TR_sl.RsolZ = 7970
        'PtR.RlgY = 0.014
        'PtR.RlgZ = PtR.RlgZ - (Tyre.UnRadius - Tyre.Defl)
        ChgtRep.Tor_Rsol_Rlg TR_sl
    End If

    TGt_sl.RlgX = TR_sl.RlgX
    TGt_sl.RlgY = TR_sl.RlgY
    TGt_sl.RlgZ = TR_sl.RlgZ
    TGt_sl.RlgL = -(-((PtR.RlgY - PtB.RlgY) * TR_sl.RlgZ - (PtR.RlgZ - PtB.RlgZ) * TR_sl.RlgY))
    TGt_sl.RlgM = -(-((PtR.RlgZ - PtB.RlgZ) * TR_sl.RlgX - (PtR.RlgX - PtB.RlgX) * TR_sl.RlgZ))
    TGt_sl.RlgN = -(-((PtR.RlgX - PtB.RlgX) * TR_sl.RlgY - (PtR.RlgY - PtB.RlgY) * TR_sl.RlgX))
    ChgtRep.Tor_Rlg_Rsol TGt_sl
    TbCal(i, 33) = TGt_sl.RlgX
    TbCal(i, 34) = TGt_sl.RlgZ
    TbCal(i, 35) = TGt_sl.RlgM
    TbCal(i, 36) = TGt_sl.RsolX / 1000: TbCalSum(i, 11) = TGt_sl.RsolX
    TbCal(i, 37) = TGt_sl.RsolY / 1000: TbCalSum(i, 12) = TGt_sl.RsolY
    TbCal(i, 38) = TGt_sl.RsolZ / 1000: TbCalSum(i, 13) = TGt_sl.RsolZ
    TbCal(i, 39) = TGt_sl.RsolL: TbCalSum(i, 14) = TGt_sl.RsolL
    TbCal(i, 40) = TGt_sl.RsolM: TbCalSum(i, 15) = TGt_sl.RsolM
    TbCal(i, 41) = TGt_sl.RsolN: TbCalSum(i, 16) = TGt_sl.RsolN

    'calul AC Vz
    'VitMs.RsolZ = -(PtB.RsolZ - ZbSolTamp) / It * 1000 ' en mm
    TbCal(i, 31) = VitMs.RsolZ

    'Calcul effort dans les guidage
    NLG.XR = Sqr(TR_sl.RlgX ^ 2 + TR_sl.RlgY ^ 2)
    NLG.XGb = -(PtR.RlgZ - PtGt.RlgZ) * NLG.XR / (PtGb.RlgZ - PtGt.RlgZ): TbCal(i, 20) = NLG.XGb
    NLG.XGt = -NLG.XGb - NLG.XR: TbCal(i, 21) = NLG.XGt
    TbCal(i, 16) = NLG.FFriBag
    TbCal(i, 28) = NLG.FFriBag + NLG.FFriJoi
    If Abs(NLG.v) > 0.05 And NLG.D > 0 Then
    TbCal(i, 29) = Sgn(NLG.v) * NLG.Fhyd / (NLG.v) ^ 2
    End If
    TbCal(i, 30) = Tyre.Omega * 60 / (2 * Pi)
    TbCal(i, 32) = NLG.Pc / 100000 'conversion en bar
    TbCal(i, 42) = NLG.Pd / 100000 'conversion en bar
    TbCal(i, 43) = NLG.Pg / 100000 'conversion en bar

Next

'Affichage
Call Affichage

Application.Calculation = xlAutomatic 'Réactive les calculs.

End Sub

Sub Affichage()

    Worksheets("Results NLG").Activate
    ActiveSheet.Cells.Select
    Selection.Clear
    Worksheets("NLG").Activate
    ActiveSheet.Cells(1, 1).Select

'0: temps; 1: AccMs.RlgZ; 2: VitMs.RlgZ; 3: DepMs.RlgZ 4: AccMns.RlgZ; 5: VitMns.RlgZ; 6: DepMns.RlgZ
'7: PtR.RlgZ; 8: Tyre.Defl; 9: NLG.v 10: NLG.d 11: NLG.Ftot 12 :NLG.Fhyd 13: Tyre.FTyre 14: NLG.FFriJoi
'15: NLG.FGas 16: NLG.FFriBag 17:PtB.RlgZ 18:PtGb.RlgZ 19:PtGt.RlgZ 20:NLG.XGb 21:NLG.XGt
'22: Tyre.Alpha 22: Tyre.Omega 23: TR_sl.RsolX 24: Tyre.Mu 25: Tyre.Slip 26:PtB.RSolZ
'27 : VGR (TR_sl.RsolZ  28 : Total friction 29: Metering pin Damping factor 30 :Tyre.Omega 31 :AC Vz
'32 : NLG.Pc
Sheets("Results NLG").Cells(2, 2) = "Temps (s)"
Sheets("Results NLG").Cells(2, 3) = "AccMs.RsolZ"
Sheets("Results NLG").Cells(2, 4) = "VitMs.RsolZ"
Sheets("Results NLG").Cells(2, 5) = "DepMs.RsolZ"
Sheets("Results NLG").Cells(2, 6) = "AccMns.RlgZ"
Sheets("Results NLG").Cells(2, 7) = "VitMns.RlgZ"
Sheets("Results NLG").Cells(2, 8) = "DepMns.RlgZ"
Sheets("Results NLG").Cells(2, 9) = "PtR.RlgZ"
Sheets("Results NLG").Cells(2, 10) = "Tyre.Defl"
Sheets("Results NLG").Cells(2, 11) = "NLG.v"
Sheets("Results NLG").Cells(2, 12) = "NLG.d"
Sheets("Results NLG").Cells(2, 13) = "NLG.Ftot"
Sheets("Results NLG").Cells(2, 14) = "NLG.Fhyd"
Sheets("Results NLG").Cells(2, 15) = "Tyre.FTyre"
Sheets("Results NLG").Cells(2, 16) = "NLG.FFriJoi"
Sheets("Results NLG").Cells(2, 17) = "NLG.FGas"
Sheets("Results NLG").Cells(2, 18) = "NLG.FFriBag"
Sheets("Results NLG").Cells(2, 19) = "PtB.RlgZ"
Sheets("Results NLG").Cells(2, 20) = "PtGb.RlgZ"
Sheets("Results NLG").Cells(2, 21) = "PtGt.RlgZ"
Sheets("Results NLG").Cells(2, 22) = "NLG.XGb"
Sheets("Results NLG").Cells(2, 23) = "NLG.XGt"
Sheets("Results NLG").Cells(2, 24) = "Tyre.Alpha"
Sheets("Results NLG").Cells(2, 25) = "Tyre.Omega"
Sheets("Results NLG").Cells(2, 26) = "TR_sl.RsolX"
Sheets("Results NLG").Cells(2, 27) = "Tyre.Mu"
Sheets("Results NLG").Cells(2, 28) = "Tyre.Slip"
Sheets("Results NLG").Cells(2, 29) = "VGR"
Sheets("Results NLG").Cells(2, 30) = "Total friction"
Sheets("Results NLG").Cells(2, 31) = "Metering pin Damping factor"
Sheets("Results NLG").Cells(2, 32) = "Tyre.Omega"
Sheets("Results NLG").Cells(2, 33) = "Ac Vz"
Sheets("Results NLG").Cells(2, 34) = "NLG.Pc"
Sheets("Results NLG").Cells(2, 35) = "Fx ptB (kN) /lg"
Sheets("Results NLG").Cells(2, 36) = "Fz ptB (kN)/lg"
Sheets("Results NLG").Cells(2, 37) = "M/y ptB (N.m) /lg"
Sheets("Results NLG").Cells(2, 38) = "Fx ptB (kN) /sol"
Sheets("Results NLG").Cells(2, 39) = "Fy ptB (kN) /sol"
Sheets("Results NLG").Cells(2, 40) = "Fz ptB (kN)/sol"
Sheets("Results NLG").Cells(2, 41) = "M/x ptB (N.m) /sol"
Sheets("Results NLG").Cells(2, 42) = "M/y ptB (N.m) /sol"
Sheets("Results NLG").Cells(2, 43) = "M/z ptB (N.m) /sol"
Sheets("Results NLG").Cells(2, 44) = "NLG.Pd"
Sheets("Results NLG").Cells(2, 45) = "NLG.Pg"
Sheets("Results NLG").Cells(2, 47) = "Tyre.FSpin"
Sheets("Results NLG").Cells(2, 48) = "Tyre.Vitx"
Sheets("Results NLG").Cells(2, 49) = "Tyre.Depx"

For i = 0 To Application.WorksheetFunction.RoundDown(NbItCal / CoeffAffich, 0)
    For j = 0 To NbAffich
        Sheets("Results NLG").Cells(3 + i, j + 2) = TbCal(i * CoeffAffich, j)
    Next
Next

End Sub

Sub RecupData()

Set NLG = Nothing
NLG.Dp = Sheets("NLG").Cells(35, 11) / 1000 ' conversion en m
NLG.Dbh = Sheets("NLG").Cells(36, 11) / 1000 ' conversion en m
NLG.Dt = Sheets("NLG").Cells(34, 11) / 1000 ' conversion en m
NLG.c = Sheets("NLG").Cells(39, 7) / 1000 ' conversion en m
NLG.Vh = Sheets("NLG").Cells(43, 7) / 1000000 'conversion en m3
NLG.Vgbp = Sheets("NLG").Cells(42, 7) / 1000000 'conversion en m3
NLG.Vginitbp = Sheets("NLG").Cells(42, 7) / 1000000 'conversion en m3
NLG.Pinitbp = Sheets("NLG").Cells(41, 7) * 100000 'conversion en Pa
NLG.Pgtamp = NLG.Pinitbp
NLG.Vghp = Sheets("NLG").Cells(45, 7) / 1000000 'conversion en m3
NLG.Vginithp = Sheets("NLG").Cells(45, 7) / 1000000 'conversion en m3
NLG.Pinithp = Sheets("NLG").Cells(44, 7) * 100000 'conversion en Pa
NLG.Gamma = Sheets("NLG").Cells(46, 7)
'NLG.Pg = NLG.Pinit
'trou de réalim du piston de détente
NLG.DTrouPis = Sheets("NLG").Cells(41, 11) / 1000 ' conversion en m
NLG.NbTrouPis = Sheets("NLG").Cells(42, 11)
NLG.DInsideBh = Sheets("NLG").Cells(37, 11) / 1000 ' conversion en m
NLG.Lbh = Sheets("NLG").Cells(38, 11) / 1000 ' conversion en m
NLG.HauteurPisBh = Sheets("NLG").Cells(43, 11) / 1000 ' conversion en m
NLG.DTrouDiap = Sheets("NLG").Cells(44, 11) / 1000 ' conversion en m
NLG.NbTrouDiap = Sheets("NLG").Cells(45, 11) ' conversion en m
NLG.Dpis = Sheets("NLG").Cells(46, 11) / 1000 ' conversion en m
NLG.OilBulk = Sheets("NLG").Cells(36, 15) * 1000000
NLG.Vtot = (Sheets("NLG").Cells(42, 7) + Sheets("NLG").Cells(43, 7) + Sheets("NLG").Cells(45, 7)) / 1000000 'conversion en m3
NLG.BagueGuide = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
NLG.BaguePiston = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
NLG.fc = Sheets("NLG").Cells(43, 15) * 1000 ' conversion en N/m
NLG.ASeal = Sheets("NLG").Cells(42, 15) / 1000 ' conversion en N/m
NLG.BaguePiston = Sheets("NLG").Cells(60, 7) / 1000 ' conversion en m
H5606.Rho = Sheets("NLG").Cells(37, 15)
H5606.Visc = Sheets("NLG").Cells(35, 15) / 1000000 'conversion en m²/s
H5606.Bulk = Sheets("NLG").Cells(36, 15) * 1000000 'conversion en Pa
H5606.Temp = Sheets("NLG").Cells(34, 15)

'On récupères les infos du pneu
Tyre.UnRadius = Sheets("NLG").Cells(36, 3) / 1000 'conversion en m
NbLigneTyre = Sheets("NLG").Cells(40, 2).End(xlDown).Row - 39 + 2 'on récupère le nombre de ligne du tableau du pneu on rajoute une valeur en nég et une en +
Dim tDefl() As Double 'vecteur tampon pour la déflection
Dim tLoad() As Double 'vecteur tampon pour l'effort
ReDim tDefl(NbLigneTyre - 1)
ReDim tLoad(NbLigneTyre - 1)
tDefl(0) = -10
tLoad(0) = 0
For i = 1 To NbLigneTyre - 2 'on bouble pour remplir les veteur tampon
tDefl(i) = Sheets("NLG").Cells(39 + i, 2) / 1000 'conversion en m
tLoad(i) = Sheets("NLG").Cells(39 + i, 3) * 1000 'conversion en N
Next
tDefl(NbLigneTyre - 1) = tDefl(NbLigneTyre - 2) + 0.001 '1 mm de plus
tLoad(NbLigneTyre - 1) = tLoad(NbLigneTyre - 2) * 3 'on triple l'effort
Tyre.TabDefl() = tDefl()
Tyre.TabLoad() = tLoad()
'On récupère le muslip ratio
NbLigneMu = Sheets("NLG").Cells(64, 2).End(xlDown).Row - 63  'on récupère le nombre de ligne du tableau du muslip
Dim tMuX() As Double 'vecteur tampon pour la déflection
Dim tMuY() As Double 'vecteur tampon pour l'effort
ReDim tMuX(NbLigneMu - 1)
ReDim tMuY(NbLigneMu - 1)
For i = 0 To NbLigneMu - 1 'on bouble pour remplir les veteur tampon
tMuX(i) = Sheets("NLG").Cells(64 + i, 2)
tMuY(i) = Sheets("NLG").Cells(64 + i, 3)
Next
Tyre.MuSlipX() = tMuX()
Tyre.MuSlipY() = tMuY()
Tyre.j = Sheets("NLG").Cells(35, 7)
'Springback
Tyre.cx = Sheets("NLG").Cells(65, 7)
Tyre.kx = Sheets("NLG").Cells(64, 7)
Tyre.WheelMass = Sheets("NLG").Cells(66, 7)
'On récupère les coordonées des points
ChgtRep.alfar = Sheets("NLG").Cells(37, 7) * 2 * Pi / 360
ChgtRep.alfap = Sheets("NLG").Cells(36, 7) * 2 * Pi / 360 + Sheets("NLG").Cells(8, 3) * 2 * Pi / 360
PtS.RlgX = 0
PtS.RlgY = 0
PtS.RlgZ = 0
PtR.RlgX = 0
PtR.RlgY = 0
PtR.RlgZ = Tyre.UnRadius
ChgtRep.Pt_Rlg_Rsol PtR
Tyre.Defl = Tyre.UnRadius - (PtR.RlgZ - PtS.RlgZ)
PtGb.RlgX = -Sheets("NLG").Cells(53, 7) / 1000
PtGb.RlgY = 0
PtGb.RlgZ = Tyre.UnRadius + (Sheets("NLG").Cells(54, 7) - Sheets("NLG").Cells(52, 7)) / 1000
ChgtRep.Pt_Rlg_Rsol PtGb
PtGt.RlgX = -Sheets("NLG").Cells(53, 7) / 1000
PtGt.RlgY = 0
PtGt.RlgZ = Tyre.UnRadius + (Sheets("NLG").Cells(54, 7) - Sheets("NLG").Cells(51, 7)) / 1000
ChgtRep.Pt_Rlg_Rsol PtGt
PtB.RlgX = -Sheets("NLG").Cells(53, 7) / 1000
PtB.RlgY = 0
PtB.RlgZ = Tyre.UnRadius + (Sheets("NLG").Cells(54, 7) - Sheets("NLG").Cells(50, 7)) / 1000
ChgtRep.Pt_Rlg_Rsol PtB

'On récupère les masse et torseur des poids
Lift = Sheets("NLG").Cells(7, 3)
Ms = Sheets("NLG").Cells(4, 3)
PMs.RsolZ = Ms * 9.81 * (1 - Lift) 'conversion en N
ChgtRep.Tor_Rsol_Rlg PMs
Mns = Sheets("NLG").Cells(34, 7)
PMns.RsolZ = Mns * 9.81  'conversion en N
ChgtRep.Tor_Rsol_Rlg PMns
Vx = Sheets("NLG").Cells(6, 3)
Vitesse = Sheets("NLG").Cells(5, 3)
TempsSimu = Sheets("NLG").Cells(9, 3)
It = Sheets("NLG").Cells(10, 3)

Set TR_sl = Nothing
Set TB_sl = Nothing
Set TGt_sl = Nothing

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

NLG.Qc = NLG.Sc * NLG.v

DEqBh = Sqr(Pi * NLG.SecBh / 4)
ReBh = (Abs(NLG.Qc) * DEqBh / (NLG.SecBh)) / H5606.Visc

If ReBh * DEqBh / 0.003 < 50 Then
    CdBh = (2.28 + 64 * 0.003 / (ReBh * DEqBh)) ^ (-1 / 2)
Else
    CdBh = (1.5 + 13.74 * (0.003 / (ReBh * DEqBh)) ^ (1 / 2)) ^ (-1 / 2)
End If
DEqBhdet = Sqr(Pi * NLG.SecBh / 4)
ReBhdet = (Abs(NLG.Qc) * DEqBhdet / (NLG.SecBh)) / H5606.Visc
If ReBhdet * DEqBhdet / 0.003 < 50 Then
    CdBhdet = (2.28 + 64 * 0.003 / (ReBhdet * DEqBhdet)) ^ (-1 / 2)
Else
    CdBhdet = (1.5 + 13.74 * (0.003 / (ReBhdet * DEqBhdet)) ^ (1 / 2)) ^ (-1 / 2)
End If

If NLG.Qc > 0 Then
    'NLG.DeltaPc = 1 / 2 * H5606.Rho * (NLG.Qc / (NLG.SecBh * CdBh)) ^ 2 * Sgn(NLG.Qc)
    'Test de l'intégration de la compressibilité de l'huile
    xRes(0) = NLG.Pc
    xRes(1) = NLG.Qc

    For i = 0 To 3
        f(0) = xRes(1) - NLG.Sc * NLG.v + NLG.Sc * (NLG.c - NLG.D) / H5606.Bulk * (xRes(0) - NLG.Pc) / It
        f(1) = (xRes(0) - NLG.Pg) - 1 / 2 * H5606.Rho * (xRes(1) / (NLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))
        'mPrecision  = f(0) + f(1)
        df(0, 0) = NLG.Sc * (NLG.c - NLG.D) / (H5606.Bulk * It): df(0, 1) = 1
        df(1, 0) = 1: df(1, 1) = -xRes(1) * H5606.Rho * (1 / (NLG.SecBh * CdBh)) ^ 2 * Sgn(xRes(1))

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

        NLG.DeltaPc = xRes(0) - NLG.Pg
        NLG.Qc = xRes(1)
    Next

Else

   NLG.DeltaPc = 1 / 2 * H5606.Rho * (NLG.Qc / (NLG.SecBh * CdBhdet)) ^ 2 * Sgn(NLG.Qc)
End If
'NLG.DeltaPbh = 128 * H5606.Rho * H5606.Visc * NLG.Lbh / (Pi * NLG.DInsideBh ^ 4) * NLG.Qc

RePis = (Abs(NLG.Qd) * NLG.DTrouPis / (NLG.STrouPis)) / H5606.Visc
If RePis * NLG.DTrouPis / NLG.HauteurPisBh < 50 Then
CdPis = (2.28 + 64 * NLG.HauteurPisBh / (RePis * NLG.DTrouPis)) ^ (-1 / 2)
Else
CdPis = (1.5 + 13.74 * (NLG.HauteurPisBh / (RePis * NLG.DTrouPis)) ^ (1 / 2)) ^ (-1 / 2)
End If
ReDiap = (Abs(NLG.Qd) * NLG.DTrouDiap / (NLG.STrouDiap)) / H5606.Visc
If ReDiap * NLG.DTrouDiap / 0.001 < 50 Then
CdDiap = (2.28 + 64 * 0.001 / (ReDiap * NLG.DTrouDiap)) ^ (-1 / 2)
Else
CdDiap = (1.5 + 13.74 * (0.001 / (ReDiap * NLG.DTrouDiap)) ^ (1 / 2)) ^ (-1 / 2)
End If

If NLG.Qd < 0 Then
    NLG.DeltaPd = 1 / 2 * H5606.Rho * (NLG.Qd / (NLG.STrouDiap * CdDiap)) ^ 2 * Sgn(NLG.Qd) + 1 / 2 * H5606.Rho * (NLG.Qd / (NLG.STrouPis * CdPis)) ^ 2 * Sgn(NLG.Qd)
Else
   NLG.DeltaPd = 1 / 2 * H5606.Rho * (NLG.Qd / (NLG.STrouPis * CdPis)) ^ 2 * Sgn(NLG.Qd)
End If

End Sub

Sub CalculBH()
Dim r1 As Double
Dim r2 As Double
Dim e As Double

'On récupère les données
Call RecupData
DiametreRainure = Sheets("NLG").Cells(49, 14)
r1 = NLG.Dbh / 2 * 1000
r2 = DiametreRainure / 2
NbRainure = Sheets("NLG").Cells(47, 16).End(xlToRight)
'Tableau position début
'Tableau position fin
'Tableau profondeur
ReDim TbDebutBH(NbRainure)
ReDim TbFinBH(NbRainure)
ReDim TbProfondeurBH(NbRainure)
For k = 0 To NbRainure - 1
    TbDebutBH(k) = Sheets("NLG").Cells(48, 16 + k)
    TbFinBH(k) = Sheets("NLG").Cells(49, 16 + k)
    TbProfondeurBH(k) = Sheets("NLG").Cells(50, 16 + k)
Next

'On nettoie le tableau existant
    Worksheets("NLG").Activate
    ActiveSheet.Range("J51:K551").Select
    Selection.Clear

'On calcul la section tous les mm jusqu'à la fin de course
ReDim TbBH(NLG.c * 1000, NbRainure - 1)
For k = 0 To NbRainure - 1
    'Calcul progressivité
    LongueurProgressiviteBH = Int((r2 ^ 2 - (r2 - (r1 - TbProfondeurBH(k))) ^ 2) ^ (1 / 2))
    For m = 0 To NLG.c * 1000
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
For m = 0 To NLG.c * 1000
    Sheets("NLG").Cells(51 + m, 10) = m
    For k = 0 To NbRainure - 1
        Sheets("NLG").Cells(51 + m, 11) = Sheets("NLG").Cells(51 + m, 11) + TbBH(m, k)
    Next
Next

'On récupère les infos de la BH
NbLigneBH = Sheets("NLG").Cells(51, 10).End(xlDown).Row - 48 'on récupère le nombre de ligne du tableau de BH
Dim tPos() As Double 'vecteur tampon pour la position
Dim tSec() As Double 'vecteur tampon pour la section
ReDim tPos(NbLigneBH - 1)
ReDim tSec(NbLigneBH - 1)
For k = 0 To NbLigneBH - 1 'on bouble pour remplir les veteur tampon
tPos(k) = Sheets("NLG").Cells(51 + k, 10) / 1000 - Sheets("NLG").Cells(51 + k, 11) / 2000 'conversion en m
tSec(k) = Sheets("NLG").Cells(51 + k, 11) / 1000000 'conversion en m²
Next
NLG.TabPosBh() = tPos() 'on rempli les vecteurs du NLG
NLG.TabSecBh() = tSec()

End Sub
