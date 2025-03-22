class WeightProcessor:
    def __init__(self):
        self.last_weight = 0
        self.stable_counter = 0

    def check_stabilization(self, new_weight):
        threshold = self.last_weight * 0.01  # 1% threshold
        if abs(new_weight - self.last_weight) < threshold:
            self.stable_counter += 1
        else:
            self.stable_counter = 0
            
        self.last_weight = new_weight
        return self.stable_counter >= 3  # 3 consecutive stable readings (10s total)