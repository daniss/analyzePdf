'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function PrivacyPolicyPage() {
  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl">Politique de Confidentialité</CardTitle>
          <p className="text-sm text-muted-foreground">
            Dernière mise à jour : 2 août 2025 | Conforme RGPD
          </p>
        </CardHeader>
        <CardContent className="prose prose-sm max-w-none">
          <h2>1. Responsable du Traitement</h2>
          <p>
            <strong>ComptaFlow SAS</strong><br />
            Adresse : Paris, France<br />
            Email : dpo@comptaflow.fr<br />
            Téléphone : +33 (0)1 XX XX XX XX
          </p>

          <h2>2. Données Collectées</h2>
          <h3>2.1 Données de Compte</h3>
          <ul>
            <li>Email (identifiant de connexion)</li>
            <li>Nom de l'entreprise</li>
            <li>Mot de passe (haché avec bcrypt)</li>
            <li>Date de création du compte</li>
          </ul>

          <h3>2.2 Données de Facturation</h3>
          <ul>
            <li>Informations de paiement (traitées par Stripe)</li>
            <li>Historique de facturation</li>
            <li>Plan d'abonnement actuel</li>
          </ul>

          <h3>2.3 Données de Factures</h3>
          <ul>
            <li><strong>Fichiers PDF/Images :</strong> Traités en mémoire uniquement, jamais stockés sur disque</li>
            <li><strong>Données extraites :</strong> Informations commerciales (noms, montants, dates, SIRET)</li>
            <li><strong>Métadonnées :</strong> Dates de traitement, statuts, logs d'audit</li>
          </ul>

          <h2>3. Finalités du Traitement</h2>
          <h3>3.1 Traitement des Factures</h3>
          <p><strong>Base légale :</strong> Intérêt légitime</p>
          <ul>
            <li>Extraction automatique de données commerciales</li>
            <li>Validation des numéros SIRET via l'API INSEE</li>
            <li>Génération d'exports comptables (Sage, EBP, Ciel, FEC)</li>
          </ul>

          <h3>3.2 Gestion du Compte</h3>
          <p><strong>Base légale :</strong> Exécution du contrat</p>
          <ul>
            <li>Authentification et autorisation d'accès</li>
            <li>Gestion des quotas et limitations</li>
            <li>Support technique et client</li>
          </ul>

          <h3>3.3 Facturation</h3>
          <p><strong>Base légale :</strong> Obligation légale</p>
          <ul>
            <li>Émission de factures</li>
            <li>Gestion des paiements</li>
            <li>Respect des obligations comptables et fiscales</li>
          </ul>

          <h2>4. Sécurité des Données</h2>
          <h3>4.1 Chiffrement</h3>
          <ul>
            <li><strong>En transit :</strong> HTTPS/TLS 1.3 pour toutes les communications</li>
            <li><strong>Au repos :</strong> Chiffrement AES-256 des données sensibles en base</li>
            <li><strong>Mots de passe :</strong> Hachage bcrypt avec salt</li>
          </ul>

          <h3>4.2 Traitement Conforme RGPD</h3>
          <ul>
            <li><strong>Minimisation :</strong> Traitement des fichiers en mémoire uniquement</li>
            <li><strong>Pseudonymisation :</strong> Identifiants UUID pour toutes les entités</li>
            <li><strong>Audit :</strong> Logs complets de tous les traitements</li>
          </ul>

          <h2>5. Conservation des Données</h2>
          <table className="border-collapse border border-gray-300 w-full">
            <thead>
              <tr className="bg-gray-50">
                <th className="border border-gray-300 p-2 text-left">Type de Données</th>
                <th className="border border-gray-300 p-2 text-left">Durée de Conservation</th>
                <th className="border border-gray-300 p-2 text-left">Justification</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-gray-300 p-2">Compte utilisateur</td>
                <td className="border border-gray-300 p-2">Durée de l'abonnement + 3 ans</td>
                <td className="border border-gray-300 p-2">Obligations comptables</td>
              </tr>
              <tr>
                <td className="border border-gray-300 p-2">Données extraites</td>
                <td className="border border-gray-300 p-2">10 ans</td>
                <td className="border border-gray-300 p-2">Archivage fiscal français</td>
              </tr>
              <tr>
                <td className="border border-gray-300 p-2">Fichiers PDF/Images</td>
                <td className="border border-gray-300 p-2">0 jour (mémoire uniquement)</td>
                <td className="border border-gray-300 p-2">Minimisation RGPD</td>
              </tr>
              <tr>
                <td className="border border-gray-300 p-2">Logs d'audit</td>
                <td className="border border-gray-300 p-2">3 ans</td>
                <td className="border border-gray-300 p-2">Sécurité et conformité</td>
              </tr>
            </tbody>
          </table>

          <h2>6. Partage des Données</h2>
          <h3>6.1 Sous-Traitants</h3>
          <ul>
            <li><strong>Groq (IA) :</strong> Traitement des données de factures pour extraction (États-Unis - Adequacy Decision)</li>
            <li><strong>Stripe :</strong> Traitement des paiements (Irlande - UE)</li>
            <li><strong>INSEE API :</strong> Validation des numéros SIRET (France)</li>
          </ul>

          <h3>6.2 Transferts Internationaux</h3>
          <p>
            Les transferts vers Groq (États-Unis) sont encadrés par l'Adequacy Decision de la Commission 
            européenne. Aucune donnée personnelle n'est transférée, uniquement le contenu commercial 
            des factures nécessaire à l'extraction.
          </p>

          <h2>7. Vos Droits RGPD</h2>
          <h3>7.1 Droits Disponibles</h3>
          <ul>
            <li><strong>Accès :</strong> Consultation de vos données personnelles</li>
            <li><strong>Rectification :</strong> Correction des données inexactes</li>
            <li><strong>Effacement :</strong> Suppression de vos données</li>
            <li><strong>Portabilité :</strong> Export de vos données au format CSV/JSON</li>
            <li><strong>Opposition :</strong> Refus du traitement pour motifs légitimes</li>
            <li><strong>Limitation :</strong> Restriction temporaire du traitement</li>
          </ul>

          <h3>7.2 Exercer vos Droits</h3>
          <p>
            <strong>En ligne :</strong> Interface dédiée dans votre compte utilisateur<br />
            <strong>Email :</strong> dpo@comptaflow.fr<br />
            <strong>Délai de réponse :</strong> 30 jours maximum
          </p>

          <h2>8. Cookies et Traceurs</h2>
          <h3>8.1 Cookies Essentiels</h3>
          <ul>
            <li><strong>access_token :</strong> Authentification (7 jours)</li>
            <li><strong>user :</strong> Cache des données utilisateur (7 jours)</li>
          </ul>

          <h3>8.2 Pas de Cookies Publicitaires</h3>
          <p>
            ComptaFlow n'utilise aucun cookie de suivi publicitaire ou d'analytics tiers. 
            Nous respectons votre vie privée sans compromis.
          </p>

          <h2>9. Notifications de Violation</h2>
          <p>
            En cas de violation de données susceptible d'engendrer un risque élevé pour vos droits, 
            nous vous notifierons dans les 72 heures conformément à l'article 34 du RGPD.
          </p>

          <h2>10. Délégué à la Protection des Données</h2>
          <p>
            <strong>Contact DPO :</strong> dpo@comptaflow.fr<br />
            <strong>Mission :</strong> Veiller au respect du RGPD et traiter vos demandes
          </p>

          <h2>11. Autorité de Contrôle</h2>
          <p>
            Vous pouvez introduire une réclamation auprès de la CNIL :<br />
            <strong>Site web :</strong> www.cnil.fr<br />
            <strong>Adresse :</strong> 3 Place de Fontenoy, TSA 80715, 75334 Paris Cedex 07
          </p>

          <div className="mt-8 p-4 bg-green-50 rounded-lg">
            <h3 className="text-sm font-semibold text-green-900">Engagement de Transparence</h3>
            <p className="text-sm text-green-800 mt-1">
              ComptaFlow s'engage à une transparence totale sur le traitement de vos données. 
              Cette politique est mise à jour régulièrement pour refléter nos pratiques et 
              l'évolution réglementaire.
            </p>
          </div>

          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h3 className="text-sm font-semibold text-blue-900">Certification et Audits</h3>
            <p className="text-sm text-blue-800 mt-1">
              Nos pratiques de protection des données font l'objet d'audits réguliers. 
              Nous respectons les référentiels de sécurité ANSSI et les bonnes pratiques 
              de la CNIL pour les professionnels comptables.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}