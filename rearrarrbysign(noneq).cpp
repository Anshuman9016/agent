class Solution {
public:
    void rearrange(vector<int> &arr) {
        vector<int> pos, neg;
        int n = arr.size();
        
        // Step 1: Separate positive and negative numbers
        for(int i = 0; i < n; i++) {
            if(arr[i] >= 0) { // Note: If your platform considers 0 as positive, change this to >= 0
                pos.push_back(arr[i]);
            }
            else {
                neg.push_back(arr[i]);
            }
        }
        
        // Step 2: Alternate elements back into the original array
        if(pos.size() > neg.size()) {
            for(int i = 0; i < neg.size(); i++) {
                arr[2*i] = pos[i];
                arr[2*i+1] = neg[i];
            }
            int index = neg.size() * 2;
            for(int i = neg.size(); i < pos.size(); i++) {
                arr[index] = pos[i];
                index++;
            }
        }
        else {
            for(int i = 0; i < pos.size(); i++) {
                arr[2*i] = pos[i];
                arr[2*i+1] = neg[i];
            }
            int index = pos.size() * 2;
            for(int i = pos.size(); i < neg.size(); i++) {
                arr[index] = neg[i];
                index++;
            }
        }
        // FIXED: Removed "return arr;" since the function return type is void
    } 
}; // FIXED: Removed the extra structural closing brace