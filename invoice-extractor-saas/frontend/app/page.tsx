import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowRight, FileText, Zap, Shield, BarChart3, Clock, Download, Sparkles, Bot, Check } from "lucide-react"

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 w-full glass border-b border-white/10">
        <div className="container flex h-20 items-center">
          <div className="mr-4 flex">
            <Link href="/" className="mr-6 flex items-center space-x-3 group">
              <div className="relative">
                <div className="absolute inset-0 gradient-primary rounded-lg blur opacity-75 group-hover:opacity-100 transition-opacity"></div>
                <div className="relative bg-white rounded-lg p-1.5">
                  <Bot className="h-6 w-6 text-primary" />
                </div>
              </div>
              <span className="font-bold text-xl bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                ComptaFlow France
              </span>
            </Link>
          </div>
          <div className="flex flex-1 items-center justify-end space-x-4">
            <nav className="hidden md:flex items-center space-x-8">
              <Link href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Fonctionnalités
              </Link>
              <Link href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Tarifs
              </Link>
              <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Tableau de Bord
              </Link>
            </nav>
            <Button asChild size="lg" className="gradient-primary text-white border-0 shadow-lg hover:shadow-xl transition-shadow">
              <Link href="/auth/signin">
                Commencer
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 py-32 sm:py-40 lg:px-8 gradient-mesh">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[800px] bg-gradient-to-r from-primary/20 via-transparent to-primary/20 rounded-full blur-3xl opacity-30"></div>
          <div className="absolute top-20 right-20 w-72 h-72 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-2xl opacity-40"></div>
          <div className="absolute bottom-20 left-20 w-96 h-96 bg-gradient-to-br from-blue-400/20 to-cyan-400/20 rounded-full blur-2xl opacity-30"></div>
        </div>
        
        <div className="mx-auto max-w-4xl text-center animate-fade-in">
          <div className="mb-8 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 text-sm font-medium text-primary">
            <Sparkles className="h-4 w-4" />
            Spécialisé pour les Experts-Comptables Français
          </div>
          
          <h1 className="text-5xl font-bold tracking-tight sm:text-7xl lg:text-8xl mb-8">
            Révolutionnez
            <span className="block bg-gradient-to-r from-primary via-purple-500 to-primary bg-clip-text text-transparent animate-slide-up">
              Votre Comptabilité
            </span>
            <span className="text-4xl sm:text-5xl lg:text-6xl text-muted-foreground font-normal">en quelques secondes</span>
          </h1>
          
          <p className="mt-8 text-xl leading-8 text-muted-foreground max-w-2xl mx-auto">
            La solution française pour les experts-comptables : traitement automatique des factures avec
            <span className="text-foreground font-semibold"> 99% de précision</span>
            et conformité GDPR garantie
          </p>
          
          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="xl" asChild className="gradient-primary text-white border-0 shadow-2xl hover:shadow-primary/25 transition-all duration-300 animate-scale-in w-full sm:w-auto">
              <Link href="/auth/signup" className="text-lg px-8 py-4">
                Commencer Gratuitement
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="ghost" size="xl" asChild className="text-lg hover:bg-primary/5 w-full sm:w-auto">
              <Link href="#demo" className="px-8 py-4">
                Voir la Démo
              </Link>
            </Button>
          </div>
          
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              Sans carte bancaire
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              5 factures gratuites/mois
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              Configuration en 2 minutes
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container py-24 sm:py-32">
        <div className="mx-auto max-w-3xl text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-muted text-sm font-medium text-muted-foreground mb-6">
            <Sparkles className="h-4 w-4" />
            Solution Certifiée pour la France
          </div>
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl mb-6">
            Tout ce dont vous avez besoin pour
            <span className="block text-primary">votre comptabilité française</span>
          </h2>
          <p className="text-xl text-muted-foreground">
            Spécialement conçu pour les experts-comptables français : SIREN/SIRET, TVA, Plan Comptable Général
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 group-hover:from-primary/30 group-hover:to-primary/20 transition-colors">
                <Zap className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="text-xl mb-2">Traitement Instantané</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Traitement des factures françaises en moins de 10 secondes avec reconnaissance SIREN/SIRET automatique
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-green-500/10 group-hover:from-green-500/30 group-hover:to-green-500/20 transition-colors">
                <Shield className="h-8 w-8 text-green-600" />
              </div>
              <CardTitle className="text-xl mb-2">Conformité Française</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Extraction des 24+ champs obligatoires français avec validation automatique des numéros SIREN/SIRET
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-500/10 group-hover:from-blue-500/30 group-hover:to-blue-500/20 transition-colors">
                <FileText className="h-8 w-8 text-blue-600" />
              </div>
              <CardTitle className="text-xl mb-2">Formats Français</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Compatible avec tous les formats de factures françaises, y compris les modèles complexes multi-pages
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-purple-500/10 group-hover:from-purple-500/30 group-hover:to-purple-500/20 transition-colors">
                <BarChart3 className="h-8 w-8 text-purple-600" />
              </div>
              <CardTitle className="text-xl mb-2">Export Sage, EBP, Ciel</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Export direct vers vos logiciels comptables français : Sage, EBP, Ciel, plus format FEC pour la DGFiP
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-500/10 group-hover:from-orange-500/30 group-hover:to-orange-500/20 transition-colors">
                <Clock className="h-8 w-8 text-orange-600" />
              </div>
              <CardTitle className="text-xl mb-2">Traitement par Lot</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Traitez jusqu&apos;à 100+ factures simultanément pour un gain de temps maximum sur vos saisies
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-teal-500/10 group-hover:from-teal-500/30 group-hover:to-teal-500/20 transition-colors">
                <Download className="h-8 w-8 text-teal-600" />
              </div>
              <CardTitle className="text-xl mb-2">Économies Garanties</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Réduisez vos coûts de saisie de 12€ à 3€ par facture, soit 75% d&apos;économies sur votre poste de travail
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-32 sm:py-40 bg-gradient-to-b from-muted/30 to-background">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center mb-20">
            <h2 className="text-4xl font-bold tracking-tight sm:text-5xl mb-6">
              Comment ça marche
            </h2>
            <p className="text-xl text-muted-foreground">
              Trois étapes simples pour automatiser votre saisie comptable française
            </p>
          </div>

          <div className="mx-auto max-w-5xl">
            <div className="grid gap-12 md:gap-16 md:grid-cols-3 relative">
              {/* Connection lines */}
              <div className="hidden md:block absolute top-20 left-1/3 right-1/3 h-0.5 bg-gradient-to-r from-primary/50 via-primary to-primary/50"></div>
              
              <div className="text-center group">
                <div className="mx-auto mb-8 relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full gradient-primary text-white text-2xl font-bold shadow-2xl">
                    1
                  </div>
                </div>
                <h3 className="mb-4 text-2xl font-semibold">Importer la Facture</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Glissez-déposez vos factures PDF françaises dans notre plateforme sécurisée et conforme GDPR
                </p>
              </div>
              
              <div className="text-center group">
                <div className="mx-auto mb-8 relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full gradient-primary text-white text-2xl font-bold shadow-2xl">
                    2
                  </div>
                </div>
                <h3 className="mb-4 text-2xl font-semibold">Traitement Automatique</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Le système reconnait automatiquement SIREN, SIRET, TVA et tous les champs obligatoires français
                </p>
              </div>
              
              <div className="text-center group">
                <div className="mx-auto mb-8 relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full gradient-primary text-white text-2xl font-bold shadow-2xl">
                    3
                  </div>
                </div>
                <h3 className="mb-4 text-2xl font-semibold">Export Comptable</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Export direct vers Sage, EBP, Ciel ou format FEC pour l&apos;administration fiscale
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="container py-32 sm:py-40">
        <div className="mx-auto max-w-3xl text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-muted text-sm font-medium text-muted-foreground mb-6">
            Tarifs Adaptés aux Experts-Comptables
          </div>
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl mb-6">
            Choisissez votre formule
          </h2>
          <p className="text-xl text-muted-foreground">
            Tarification transparente qui s&apos;adapte à la taille de votre cabinet comptable
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 lg:grid-cols-3">
          <Card className="card-modern hover:shadow-2xl transition-all duration-300">
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Découverte</CardTitle>
              <CardDescription className="text-lg">Parfait pour tester avec vos premiers clients</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">0€</span>
                <span className="text-xl text-muted-foreground">/mois</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  5 factures françaises/mois
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Reconnaissance SIREN/SIRET
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Export CSV/JSON français
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Support par email
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" size="lg" asChild>
                <Link href="/auth/signup">Commencer Gratuitement</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="card-modern border-primary/50 shadow-2xl shadow-primary/10 relative overflow-hidden hover:shadow-3xl transition-all duration-300 scale-105">
            <div className="absolute top-0 left-0 right-0 h-1 gradient-primary"></div>
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-primary text-primary-foreground text-sm font-medium rounded-full">
              Most Popular
            </div>
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Cabinet Standard</CardTitle>
              <CardDescription className="text-lg">Pour cabinets 1-5 collaborateurs (20-50 clients)</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">39€</span>
                <span className="text-xl text-muted-foreground">/mois</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  150 factures/mois
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Tous exports : Sage, EBP, Ciel, FEC
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Validation conformité française
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Traitement par lots
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Support prioritaire expert-comptable
                </li>
              </ul>
              <Button className="mt-8 w-full gradient-primary text-white border-0 shadow-lg" size="lg" asChild>
                <Link href="/auth/signup">Essai Gratuit 14 Jours</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="card-modern hover:shadow-2xl transition-all duration-300">
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Cabinet Premium</CardTitle>
              <CardDescription className="text-lg">Pour gros cabinets 5-15 collaborateurs (100+ clients)</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">129€</span>
                <span className="text-xl text-muted-foreground">/mois</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  600 factures/mois
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  API pour intégration personnalisée
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Formation équipe incluse
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Champs personnalisés cabinet
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Support dédié + hotline
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" size="lg" asChild>
                <Link href="/auth/signup">Nous Contacter</Link>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 sm:py-40 gradient-mesh relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-primary/5"></div>
        <div className="container relative">
          <div className="mx-auto max-w-4xl text-center">
            <h2 className="text-4xl font-bold tracking-tight sm:text-6xl mb-8">
              Prêt à automatiser votre
              <span className="block text-primary">saisie comptable ?</span>
            </h2>
            <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto leading-relaxed">
              Rejoignez des centaines d&apos;experts-comptables qui économisent déjà 15-30 minutes par client chaque mois
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="xl" asChild className="gradient-primary text-white border-0 shadow-2xl hover:shadow-primary/25 transition-all duration-300 w-full sm:w-auto">
                <Link href="/auth/signup" className="text-lg px-10 py-6">
                  Commencer Maintenant
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button variant="ghost" size="xl" asChild className="text-lg hover:bg-primary/5 w-full sm:w-auto">
                <Link href="#demo" className="px-10 py-6">
                  Voir la Démo
                </Link>
              </Button>
            </div>
            <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-8 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                Essai gratuit 14 jours
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                Résiliation à tout moment
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                Aucun frais d&apos;installation
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-muted/30 py-16">
        <div className="container">
          <div className="flex flex-col items-center justify-between gap-8 md:flex-row">
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="absolute inset-0 gradient-primary rounded-lg blur opacity-75"></div>
                <div className="relative bg-white rounded-lg p-1.5">
                  <Bot className="h-6 w-6 text-primary" />
                </div>
              </div>
              <span className="font-bold text-xl bg-gradient-to-r from-primary to-primary/80 bg-clip-text text-transparent">
                ComptaFlow France
              </span>
            </div>
            <div className="flex flex-col items-center gap-2 md:items-end">
              <p className="text-sm text-muted-foreground">
                Solution française pour experts-comptables
              </p>
              <p className="text-xs text-muted-foreground">
                © 2024 ComptaFlow France. Tous droits réservés.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}