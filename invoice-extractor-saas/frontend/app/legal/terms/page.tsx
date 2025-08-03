'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function TermsOfServicePage() {
  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Conditions Générales d'Utilisation</CardTitle>
          <p className="text-sm text-muted-foreground">
            Dernière mise à jour : 2 août 2025
          </p>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <h2>1. Objet et Champ d'Application</h2>
          <p>
            Les présentes Conditions Générales d'Utilisation (CGU) régissent l'utilisation de la plateforme 
            ComptaFlow, service d'extraction intelligente de données de factures destiné aux experts-comptables 
            et professionnels de la comptabilité en France.
          </p>

          <h2>2. Définitions</h2>
          <ul>
            <li><strong>Plateforme :</strong> Le service ComptaFlow accessible via l'interface web</li>
            <li><strong>Utilisateur :</strong> Toute personne physique ou morale utilisant la Plateforme</li>
            <li><strong>Factures :</strong> Documents commerciaux téléversés pour traitement</li>
            <li><strong>Données Extraites :</strong> Informations extraites des factures par l'IA</li>
          </ul>

          <h2>3. Accès au Service</h2>
          <h3>3.1 Inscription</h3>
          <p>
            L'accès à ComptaFlow nécessite la création d'un compte utilisateur. L'Utilisateur s'engage à 
            fournir des informations exactes et à maintenir la confidentialité de ses identifiants.
          </p>

          <h3>3.2 Plans Tarifaires</h3>
          <ul>
            <li><strong>Gratuit :</strong> 10 factures/mois, fonctionnalités de base</li>
            <li><strong>Pro :</strong> 29€/mois, 500 factures/mois, support prioritaire</li>
            <li><strong>Business :</strong> 59€/mois, 2000 factures/mois, accès API</li>
            <li><strong>Enterprise :</strong> 99€/mois, factures illimitées, fonctionnalités avancées</li>
          </ul>

          <h2>4. Utilisation du Service</h2>
          <h3>4.1 Usage Conforme</h3>
          <p>
            L'Utilisateur s'engage à utiliser ComptaFlow uniquement pour le traitement de factures 
            légitimes dans le cadre de son activité professionnelle.
          </p>

          <h3>4.2 Restrictions</h3>
          <p>Il est interdit de :</p>
          <ul>
            <li>Téléverser des documents contenant des données illégales ou sensibles</li>
            <li>Contourner les limitations techniques ou de quota</li>
            <li>Utiliser le service à des fins de reverse engineering</li>
            <li>Partager ses identifiants avec des tiers</li>
          </ul>

          <h2>5. Protection des Données</h2>
          <h3>5.1 Conformité RGPD</h3>
          <p>
            ComptaFlow traite les données personnelles en conformité avec le Règlement Général sur la 
            Protection des Données (RGPD) et la Loi Informatique et Libertés française.
          </p>

          <h3>5.2 Traitement des Factures</h3>
          <p>
            Les factures sont traitées exclusivement en mémoire, sans stockage permanent non chiffré. 
            Seules les données extraites sont conservées de manière chiffrée pour permettre les exports 
            comptables.
          </p>

          <h2>6. Responsabilités</h2>
          <h3>6.1 Responsabilité de ComptaFlow</h3>
          <p>
            ComptaFlow s'engage à fournir un service de qualité mais ne garantit pas l'exactitude 
            à 100% des données extraites. L'Utilisateur demeure responsable de la vérification des 
            données avant intégration comptable.
          </p>

          <h3>6.2 Responsabilité de l'Utilisateur</h3>
          <p>
            L'Utilisateur est responsable de la conformité des documents téléversés et de l'usage 
            des données extraites selon la réglementation comptable française.
          </p>

          <h2>7. Propriété Intellectuelle</h2>
          <p>
            ComptaFlow conserve tous les droits de propriété intellectuelle sur la plateforme, 
            les algorithmes et l'interface. Les données extraites appartiennent à l'Utilisateur.
          </p>

          <h2>8. Facturation et Résiliation</h2>
          <h3>8.1 Facturation</h3>
          <p>
            Les abonnements payants sont facturés mensuellement. Le paiement s'effectue par carte 
            bancaire via Stripe.
          </p>

          <h3>8.2 Résiliation</h3>
          <p>
            L'abonnement peut être résilié à tout moment depuis l'interface utilisateur. 
            La résiliation prend effet à la fin de la période de facturation en cours.
          </p>

          <h2>9. Modifications</h2>
          <p>
            ComptaFlow se réserve le droit de modifier ces CGU. Les utilisateurs seront informés 
            par email des modifications importantes avec un préavis de 30 jours.
          </p>

          <h2>10. Droit Applicable</h2>
          <p>
            Les présentes CGU sont régies par le droit français. Tout litige sera soumis à la 
            compétence exclusive des tribunaux de Paris.
          </p>

          <h2>11. Contact</h2>
          <p>
            Pour toute question relative aux présentes CGU :
            <br />
            Email : support@comptaflow.fr
            <br />
            Adresse : ComptaFlow SAS, Paris, France
          </p>

          <div className="mt-8 p-4 bg-blue-50 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-900">Conformité Réglementaire</h3>
            <p className="text-sm text-blue-800 mt-1">
              ComptaFlow respecte les normes françaises de sécurité des données, les exigences 
              du Plan Comptable Général (PCG) et les obligations de l'Administration Fiscale 
              concernant l'archivage électronique des factures.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}