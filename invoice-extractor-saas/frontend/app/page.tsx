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
                InvoiceAI
              </span>
            </Link>
          </div>
          <div className="flex flex-1 items-center justify-end space-x-4">
            <nav className="hidden md:flex items-center space-x-8">
              <Link href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Pricing
              </Link>
              <Link href="/dashboard" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Dashboard
              </Link>
            </nav>
            <Button asChild size="lg" className="gradient-primary text-white border-0 shadow-lg hover:shadow-xl transition-shadow">
              <Link href="/auth/signin">
                Get Started
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
            Powered by Claude 4 AI Vision
          </div>
          
          <h1 className="text-5xl font-bold tracking-tight sm:text-7xl lg:text-8xl mb-8">
            Transform
            <span className="block bg-gradient-to-r from-primary via-purple-500 to-primary bg-clip-text text-transparent animate-slide-up">
              Invoice Processing
            </span>
            <span className="text-4xl sm:text-5xl lg:text-6xl text-muted-foreground font-normal">in seconds</span>
          </h1>
          
          <p className="mt-8 text-xl leading-8 text-muted-foreground max-w-2xl mx-auto">
            Experience the future of document processing with AI that sees, understands, and extracts data with
            <span className="text-foreground font-semibold"> 99% accuracy</span>
          </p>
          
          <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button size="xl" asChild className="gradient-primary text-white border-0 shadow-2xl hover:shadow-primary/25 transition-all duration-300 animate-scale-in w-full sm:w-auto">
              <Link href="/auth/signup" className="text-lg px-8 py-4">
                Start Processing Now
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
            </Button>
            <Button variant="ghost" size="xl" asChild className="text-lg hover:bg-primary/5 w-full sm:w-auto">
              <Link href="#demo" className="px-8 py-4">
                See it in Action
              </Link>
            </Button>
          </div>
          
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-6 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              No credit card required
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              5 free invoices monthly
            </div>
            <div className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              Setup in under 2 minutes
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container py-24 sm:py-32">
        <div className="mx-auto max-w-3xl text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-muted text-sm font-medium text-muted-foreground mb-6">
            <Sparkles className="h-4 w-4" />
            Powered by Claude 4 Vision
          </div>
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl mb-6">
            Everything you need for
            <span className="block text-primary">modern invoice processing</span>
          </h2>
          <p className="text-xl text-muted-foreground">
            Built with cutting-edge AI technology to handle any invoice format with unprecedented accuracy
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 group-hover:from-primary/30 group-hover:to-primary/20 transition-colors">
                <Zap className="h-8 w-8 text-primary" />
              </div>
              <CardTitle className="text-xl mb-2">Lightning Fast</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Process invoices in under 10 seconds using Claude 4&apos;s advanced vision capabilities
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500/20 to-green-500/10 group-hover:from-green-500/30 group-hover:to-green-500/20 transition-colors">
                <Shield className="h-8 w-8 text-green-600" />
              </div>
              <CardTitle className="text-xl mb-2">99% Accuracy</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Claude 4&apos;s advanced vision AI ensures industry-leading extraction accuracy
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-500/10 group-hover:from-blue-500/30 group-hover:to-blue-500/20 transition-colors">
                <FileText className="h-8 w-8 text-blue-600" />
              </div>
              <CardTitle className="text-xl mb-2">Any Format</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Handles PDFs, images, and scanned documents with various layouts seamlessly
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-purple-500/20 to-purple-500/10 group-hover:from-purple-500/30 group-hover:to-purple-500/20 transition-colors">
                <BarChart3 className="h-8 w-8 text-purple-600" />
              </div>
              <CardTitle className="text-xl mb-2">Smart Analytics</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Track processing metrics and gain insights into your invoice data patterns
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-500/10 group-hover:from-orange-500/30 group-hover:to-orange-500/20 transition-colors">
                <Clock className="h-8 w-8 text-orange-600" />
              </div>
              <CardTitle className="text-xl mb-2">Batch Processing</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Upload and process multiple invoices simultaneously for maximum efficiency
              </CardDescription>
            </CardHeader>
          </Card>

          <Card className="card-modern group hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300 hover:-translate-y-1">
            <CardHeader className="pb-4">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500/20 to-teal-500/10 group-hover:from-teal-500/30 group-hover:to-teal-500/20 transition-colors">
                <Download className="h-8 w-8 text-teal-600" />
              </div>
              <CardTitle className="text-xl mb-2">Export Options</CardTitle>
              <CardDescription className="text-base leading-relaxed">
                Download as CSV, JSON, or integrate directly with your accounting software
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
              How it works
            </h2>
            <p className="text-xl text-muted-foreground">
              Three simple steps to transform your invoice processing workflow
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
                <h3 className="mb-4 text-2xl font-semibold">Upload Invoice</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Simply drag and drop your PDF or image files into our secure, encrypted platform
                </p>
              </div>
              
              <div className="text-center group">
                <div className="mx-auto mb-8 relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full gradient-primary text-white text-2xl font-bold shadow-2xl">
                    2
                  </div>
                </div>
                <h3 className="mb-4 text-2xl font-semibold">AI Processing</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Claude 4 AI analyzes and extracts all invoice data with remarkable precision
                </p>
              </div>
              
              <div className="text-center group">
                <div className="mx-auto mb-8 relative">
                  <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl group-hover:blur-2xl transition-all duration-300"></div>
                  <div className="relative flex h-20 w-20 items-center justify-center rounded-full gradient-primary text-white text-2xl font-bold shadow-2xl">
                    3
                  </div>
                </div>
                <h3 className="mb-4 text-2xl font-semibold">Export Data</h3>
                <p className="text-lg text-muted-foreground leading-relaxed">
                  Download structured data instantly or integrate with your existing tools
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
            Simple Pricing
          </div>
          <h2 className="text-4xl font-bold tracking-tight sm:text-5xl mb-6">
            Choose your plan
          </h2>
          <p className="text-xl text-muted-foreground">
            Transparent pricing that scales with your business needs
          </p>
        </div>

        <div className="mx-auto grid max-w-6xl grid-cols-1 gap-8 lg:grid-cols-3">
          <Card className="card-modern hover:shadow-2xl transition-all duration-300">
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Free</CardTitle>
              <CardDescription className="text-lg">Perfect for trying out our service</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">$0</span>
                <span className="text-xl text-muted-foreground">/month</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  5 invoices per month
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Claude 4 AI processing
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  CSV export
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Email support
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" size="lg" asChild>
                <Link href="/auth/signup">Get Started Free</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="card-modern border-primary/50 shadow-2xl shadow-primary/10 relative overflow-hidden hover:shadow-3xl transition-all duration-300 scale-105">
            <div className="absolute top-0 left-0 right-0 h-1 gradient-primary"></div>
            <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-primary text-primary-foreground text-sm font-medium rounded-full">
              Most Popular
            </div>
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Professional</CardTitle>
              <CardDescription className="text-lg">For growing businesses</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">$29</span>
                <span className="text-xl text-muted-foreground">/month</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  100 invoices per month
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Advanced AI extraction
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  All export formats
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  API access
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Priority support
                </li>
              </ul>
              <Button className="mt-8 w-full gradient-primary text-white border-0 shadow-lg" size="lg" asChild>
                <Link href="/auth/signup">Start Free Trial</Link>
              </Button>
            </CardContent>
          </Card>

          <Card className="card-modern hover:shadow-2xl transition-all duration-300">
            <CardHeader className="pb-8">
              <CardTitle className="text-2xl">Business</CardTitle>
              <CardDescription className="text-lg">For larger operations</CardDescription>
              <div className="mt-6">
                <span className="text-5xl font-bold">$99</span>
                <span className="text-xl text-muted-foreground">/month</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-4 text-base">
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  500 invoices per month
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Everything in Pro
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Batch processing
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Custom fields
                </li>
                <li className="flex items-center gap-3">
                  <Check className="h-5 w-5 text-green-500" />
                  Dedicated support
                </li>
              </ul>
              <Button className="mt-8 w-full" variant="outline" size="lg" asChild>
                <Link href="/auth/signup">Contact Sales</Link>
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
              Ready to transform your
              <span className="block text-primary">invoice processing?</span>
            </h2>
            <p className="text-xl text-muted-foreground mb-12 max-w-2xl mx-auto leading-relaxed">
              Join hundreds of accounting firms and businesses already saving hours every day with AI-powered invoice processing
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="xl" asChild className="gradient-primary text-white border-0 shadow-2xl hover:shadow-primary/25 transition-all duration-300 w-full sm:w-auto">
                <Link href="/auth/signup" className="text-lg px-10 py-6">
                  Start Processing Now
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Link>
              </Button>
              <Button variant="ghost" size="xl" asChild className="text-lg hover:bg-primary/5 w-full sm:w-auto">
                <Link href="#demo" className="px-10 py-6">
                  Watch Demo
                </Link>
              </Button>
            </div>
            <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-8 text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                14-day free trial
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                Cancel anytime
              </div>
              <div className="flex items-center gap-2">
                <Check className="h-5 w-5 text-green-500" />
                No setup fees
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
                InvoiceAI
              </span>
            </div>
            <div className="flex flex-col items-center gap-2 md:items-end">
              <p className="text-sm text-muted-foreground">
                Powered by Claude 4 AI Vision
              </p>
              <p className="text-xs text-muted-foreground">
                © 2024 InvoiceAI. All rights reserved.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}