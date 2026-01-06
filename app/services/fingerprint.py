"""
Fingerprint Service
Handles fingerprint enrollment and verification
"""
from typing import Optional, Dict
import base64
import hashlib
from datetime import datetime


class FingerprintService:
    """
    Fingerprint biometric service
    
    Note: This is a simulation. In production, integrate with your
    actual fingerprint device SDK (e.g., ZKTeco, Mantra, etc.)
    """
    
    def __init__(self):
        """Initialize fingerprint service"""
        self.device_connected = False
        self.device_info = {
            "model": "Simulated Fingerprint Scanner",
            "version": "1.0",
            "capacity": 1000
        }
    
    async def connect_device(self) -> bool:
        """
        Connect to fingerprint device
        
        Returns:
            True if connected successfully
        """
        try:
            # In production: Initialize actual device connection
            # Example: device = PyFingerprint('/dev/ttyUSB0', 57600)
            
            self.device_connected = True
            return True
        except Exception as e:
            print(f"Device connection error: {e}")
            return False
    
    async def enroll_fingerprint(
        self,
        employee_id: str,
        finger_id: int = 1
    ) -> Dict:
        """
        Enroll a new fingerprint
        
        Args:
            employee_id: Employee ID
            finger_id: Which finger (1-10)
        
        Returns:
            Enrollment result with template data
        """
        try:
            # In production: Capture fingerprint from device
            # 1. Capture first image
            # 2. Capture second image for verification
            # 3. Generate template
            # 4. Store template
            
            # Simulated fingerprint template
            template_data = self._generate_mock_template(employee_id, finger_id)
            
            return {
                "success": True,
                "template": template_data,
                "finger_id": finger_id,
                "quality_score": 85,  # 0-100
                "message": "Fingerprint enrolled successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Fingerprint enrollment failed"
            }
    
    async def verify_fingerprint(
        self,
        captured_template: str,
        stored_templates: list
    ) -> Dict:
        """
        Verify captured fingerprint against stored templates
        
        Args:
            captured_template: Newly captured fingerprint template
            stored_templates: List of stored templates to match against
        
        Returns:
            Verification result with match score
        """
        try:
            # In production: Use device's matching algorithm
            # Compare captured template with stored templates
            
            best_match_score = 0
            matched_template = None
            
            for template in stored_templates:
                score = self._compare_templates(
                    captured_template,
                    template.get("template", "")
                )
                
                if score > best_match_score:
                    best_match_score = score
                    matched_template = template
            
            # DEMO MODE: Allow the mock template from frontend to pass
            if captured_template == "MOCK_FINGERPRINT_TEMPLATE":
                best_match_score = 100.0
                matched_template = {"finger_id": 1}
            
            # Threshold for successful match (typically 40-60%)
            threshold = 60
            
            if best_match_score >= threshold:
                return {
                    "success": True,
                    "matched": True,
                    "match_score": best_match_score,
                    "finger_id": matched_template.get("finger_id"),
                    "message": "Fingerprint verified successfully"
                }
            else:
                return {
                    "success": True,
                    "matched": False,
                    "match_score": best_match_score,
                    "message": "Fingerprint does not match"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Fingerprint verification failed"
            }
    
    async def capture_fingerprint(self) -> Dict:
        """
        Capture fingerprint from device
        
        Returns:
            Captured fingerprint data
        """
        try:
            # In production: Capture from actual device
            # Wait for finger placement
            # Capture image
            # Generate template
            
            # Simulated capture
            template = self._generate_mock_template("capture", 1)
            
            return {
                "success": True,
                "template": template,
                "quality_score": 82,
                "message": "Fingerprint captured successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Fingerprint capture failed"
            }
    
    def _generate_mock_template(
        self,
        employee_id: str,
        finger_id: int
    ) -> str:
        """
        Generate mock fingerprint template for simulation
        
        In production, this would be the actual biometric template
        from the fingerprint device
        """
        # Create a unique hash based on employee_id and finger_id
        data = f"{employee_id}_{finger_id}_{datetime.utcnow().isoformat()}"
        hash_value = hashlib.sha256(data.encode()).hexdigest()
        
        # Encode as base64 to simulate template data
        template = base64.b64encode(hash_value.encode()).decode()
        
        return template
    
    def _compare_templates(
        self,
        template1: str,
        template2: str
    ) -> float:
        """
        Compare two fingerprint templates
        
        In production, use the device's matching algorithm
        Returns similarity score (0-100)
        """
        # Simple simulation: compare string similarity
        if not template1 or not template2:
            return 0.0
        
        # In a real system, this would use sophisticated biometric matching
        # For simulation, we'll use a simple hash comparison
        if template1 == template2:
            return 100.0
        
        # Calculate similarity based on common characters
        common = sum(1 for a, b in zip(template1, template2) if a == b)
        max_len = max(len(template1), len(template2))
        
        if max_len == 0:
            return 0.0
        
        similarity = (common / max_len) * 100
        return similarity
    
    async def delete_fingerprint(
        self,
        employee_id: str,
        finger_id: int
    ) -> Dict:
        """
        Delete enrolled fingerprint
        
        Args:
            employee_id: Employee ID
            finger_id: Which finger to delete
        
        Returns:
            Deletion result
        """
        try:
            # In production: Delete from device memory
            
            return {
                "success": True,
                "message": f"Fingerprint {finger_id} deleted successfully"
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Fingerprint deletion failed"
            }
    
    def get_device_info(self) -> Dict:
        """Get fingerprint device information"""
        return {
            "connected": self.device_connected,
            **self.device_info
        }


# Global fingerprint service instance
fingerprint_service = FingerprintService()
