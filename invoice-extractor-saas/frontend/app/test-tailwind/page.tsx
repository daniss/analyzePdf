export default function TestTailwindPage() {
  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-blue-600 mb-4">
          Tailwind CSS Test Page
        </h1>
        
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-2xl font-semibold text-gray-800 mb-3">
            Testing Tailwind Classes
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-blue-500 text-white p-4 rounded">
              Blue Box
            </div>
            <div className="bg-green-500 text-white p-4 rounded">
              Green Box
            </div>
            <div className="bg-red-500 text-white p-4 rounded">
              Red Box
            </div>
          </div>
        </div>
        
        <button className="bg-purple-600 hover:bg-purple-700 text-white font-bold py-2 px-4 rounded transition-colors">
          Test Button
        </button>
      </div>
    </div>
  )
}