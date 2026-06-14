Dans le dossier SimuLanding il y a un fichier excel. L'objectif de ce fichier excel est de pouvoir faire la simulation d'atterrissage d'un avion complet pour dimension les loi hydraulique et ressort gaz des trains d'atterrissage. 
Je vais  décrire les contenu de chaque onglet et l'objectif.
Description des onglets:
    Onglet "Projet" :
        Le premier onglet projet contien la table de révision pour tracer toutes les évolutions faite sur le projet concerné.
    Onglets "Summary MLG" et "Summary NLG"
        Les deux onglets suivants sont les onglets Summary MLG et Summary NLG, ils sont formalisés de façon à pouvoir être exporté en PDF pour être envoyé au client. 
        Il contient les données principales du train d'atterrissage concerné. 
        Il contient les courbes isotherme au température ambiantes et températures extrêmes avec les position aux statiques dont l'objectif est a préciser.
        Il contient également les résultats des simulation dans 4 condition de chute ( à définir) avec dans une première page le résumé avec les différentes valeurs maxi. puis à la suite les courbes de chque conditions de courses aux trois température.
        Il contient également un tableau qui affiche les valeurs d'effort total de de l'amortisseur en fonction de la vitesse et de la course.
    Onglet "Aircraft"
        L'onglet contient deux parties. La première concerne la simula avec l'avion complet, on affiche les courbes issue des résultats de simulaiton, le tableau permet de renseigner les conditions de chute, et le moment d'inertie de l'avion suivant l'axe y.
        La deuxième partie à partie de la ligne 23 contient toutes les données qui permette de définir les train d'atterrissage ce sont toutes les données qu'il faut renseigné pour les les trains NLG et MLG.
    Onglet Results "Aircraft"
        Cet onglet contien tous les résultats issue des calculs de simulation réalisée à partir du code présent dans les modules de macro du fichier. Le calculs est réalisé avec un pes de temps fin mais les résultats sont afficher avec un pas de temps plus gros de façon à limiter le nombre de ligne à 1000.
    L'onglet  "MLG" et "NLG"
        L'ongelt de la même façon que l'onglet Aircraft présente un tableau avec les coniguration de simulation les courbe de résultat de cette simulation puis à partir de la ligne 31 cela contient toute les données du train d'atterrissage pour pouvoir faire la simulation, mais toutes les données sont récupérer de l'onglet "Aircraft"
        L'onglet MLG fait en fait la simulation d'un train d'atterrissage à balancier., L'onglet NLG fait la simulation d'un train d'atterrissage droit. Ce sont deux type d'architecture différente.
    Les onglet "Results NLG" et "Results MLG"
        Même chose que pour l'onglet "results Aircraft" respectivement pourr le NLG et l MLG  