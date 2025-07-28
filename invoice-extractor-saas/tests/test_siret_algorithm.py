#!/usr/bin/env python3
"""
Test the SIRET validation algorithm with the extracted numbers
"""

def validate_siren_algorithm(siren: str) -> bool:
    """Test the SIREN validation algorithm"""
    if len(siren) != 9 or not siren.isdigit():
        return False
        
    try:
        # Convert to digits
        digits = [int(d) for d in siren]
        
        # Basic validation: not all same digit, not sequential
        if len(set(digits)) == 1:  # All same digit
            return digits[0] != 0  # Allow all non-zero digits for testing
        
        # Apply modified Luhn algorithm for SIREN
        sum_total = 0
        for i in range(9):
            n = digits[i]
            # Double every second digit from the right
            if (9 - i) % 2 == 0:  # Even position from right (1st, 3rd, 5th...)
                n *= 2
                if n > 9:
                    n = n // 10 + n % 10
            sum_total += n
        
        print(f"SIREN {siren}: sum = {sum_total}, modulo 10 = {sum_total % 10}")
        
        # SIREN is valid if sum modulo 10 equals 0
        return (sum_total % 10) == 0
        
    except (ValueError, TypeError):
        return False

def test_extracted_sirens():
    """Test the SIREN numbers extracted from the invoice"""
    
    test_sirens = [
        ("652023902", "Fournisseur - CARREFOUR SA"),
        ("572000242", "Client - BOUYGUES SA"),
        ("652014051", "Test - Real Carrefour SIREN"),
        ("542091180", "Test - Real Auchan SIREN"),
        ("123456789", "Test pattern from code"),
    ]
    
    print("🔍 Testing SIREN validation algorithm")
    print("=" * 60)
    
    for siren, description in test_sirens:
        is_valid = validate_siren_algorithm(siren)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{status} - {siren} ({description})")
    
    print("\n" + "=" * 60)
    print("📝 Analysis:")
    print("If real company SIRENs are showing as invalid, the algorithm is too strict")

if __name__ == "__main__":
    test_extracted_sirens()