// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

// Gerçek ZK ispatlarını doğrulayacak olan, snarkjs tarafından üretilmiş
// PDMVerifier kontratını import ediyoruz.
import "./PDMVerifier.sol";

/**
 * @title PdMSystem (Predictive Maintenance System)
 * @dev Rol bazlı erişim kontrolü, ekonomik teşvikler ve ZK ispatlarını
 * tek ve bütüncül bir sözleşmede birleştirir.
 * @author AI Assistant & PDM Team
 */
contract PdMSystem {
    // --- LIBRARIES & INTERFACES ---

    // zkVerifier adresini değiştirilemez (immutable) olarak ayarlıyoruz.
    // Bu, hem güvenliği artırır hem de deployment sırasında gaz maliyetini düşürür.
    Groth16Verifier public immutable zkVerifier;

    // --- ENUMS & STRUCTS ---

    enum Role { NONE, WORKER, ENGINEER, MANAGER, ADMIN }

    struct UserProfile {
        Role role;
        // Derleme hatalarını önlemek için string tipine geri dönüldü.
        string name;
        string department;
        uint256 registeredAt;
        bool isActive;
        // Economic Profile
        uint256 trainerStake;
        uint256 predictorStake;
        uint256 reputationScore; // İtibar Puanı (0-10000)
        uint256 totalEarnings;
        uint256 lastActivity;
        bool isBlacklisted;
    }

    struct SensorData {
        bytes32 dataCommitment;
        bytes32 metadataHash;
        address submitter;
        uint256 timestamp;
        uint256 machineId;
        Role minimumViewRole;
    }

    struct ZKModel {
        bytes32 modelCommitment;
        bytes32 modelType;
        bytes32 domainType;
        uint256 claimedAccuracy;
        address trainer;
        uint256 registrationTime;
        bool isActive;
    }
    
    // --- STATE VARIABLES ---

    // admin adresini de değiştirilemez (immutable) yapıyoruz.
    address public immutable admin;
    bool public isPaused = false;

    // Döngü kullanımını engellemek için sayaçlar
    uint256 public totalUsers;
    uint256 public engineerCount;
    uint256 public modelCounter;
    uint256 public dataCounter;

    // Mappings
    mapping(address => UserProfile) public users;
    mapping(uint256 => SensorData) public sensorData;
    mapping(uint256 => ZKModel) public models;
    mapping(bytes32 => bool) public usedCommitments;
    // Döngü yerine O(1) erişim sağlayan mapping
    mapping(address => mapping(uint256 => bool)) public hasDataAccess;

    // --- EVENTS ---

    event UserRegistered(address indexed user, Role role, string name);
    event StakeDeposited(address indexed user, uint256 amount, string stakeType);
    event StakeWithdrawn(address indexed user, uint256 amount);
    event DataSubmitted(uint256 indexed dataId, address indexed submitter, uint256 machineId);
    event ModelRegistered(uint256 indexed modelId, bytes32 indexed commitment, address indexed trainer);
    event SystemPaused(bool status);

    // --- MODIFIERS ---

    modifier onlyAdmin() { require(msg.sender == admin, "PdM:NotAdmin"); _; }
    modifier whenNotPaused() { require(!isPaused, "PdM:Paused"); _; }
    modifier onlyActiveUser() { require(users[msg.sender].isActive, "PdM:Inactive"); _; }
    modifier notBlacklisted(address user) { require(!users[user].isBlacklisted, "PdM:Blacklisted"); _; }
    modifier validModel(uint256 modelId) { require(modelId < modelCounter && models[modelId].isActive, "PdM:InvalidModel"); _; }
    modifier hasSufficientTrainerStake(address user) { require(users[user].trainerStake > 0, "PdM:TrainerStakeRequired"); _; }

    // --- CONSTRUCTOR ---

    constructor(address _verifierAddress) {
        require(_verifierAddress != address(0), "PdM:InvalidVerifier");
        admin = msg.sender;
        zkVerifier = Groth16Verifier(_verifierAddress);
        
        users[msg.sender].role = Role.ADMIN;
        users[msg.sender].name = "System Admin";
        users[msg.sender].isActive = true;
        users[msg.sender].reputationScore = 10000;
        users[msg.sender].registeredAt = block.timestamp;
        totalUsers = 1;
        emit UserRegistered(msg.sender, Role.ADMIN, "System Admin");
    }

    // --- USER & STAKE MANAGEMENT ---

    function registerUser(address userAddress, Role role, string memory _name, string memory _department) external onlyAdmin {
        require(users[userAddress].role == Role.NONE, "PdM:UserExists");
        
        users[userAddress].role = role;
        users[userAddress].name = _name;
        users[userAddress].department = _department;
        users[userAddress].isActive = true;
        users[userAddress].reputationScore = 5000; // Başlangıç itibarı
        users[userAddress].registeredAt = block.timestamp;

        totalUsers++;
        if (role >= Role.ENGINEER) {
            engineerCount++;
        }
        emit UserRegistered(userAddress, role, _name);
    }
    
    function depositStake() external payable notBlacklisted(msg.sender) {
        users[msg.sender].trainerStake += msg.value;
        emit StakeDeposited(msg.sender, msg.value, "trainer");
    }

    function withdrawStake(uint256 amount) external notBlacklisted(msg.sender) {
        // 1. CHECKS (Kontroller)
        UserProfile storage user = users[msg.sender];
        uint256 totalStake = user.trainerStake + user.predictorStake;
        require(amount > 0 && totalStake >= amount, "PdM:InsufficientStake");

        // 2. EFFECTS (State Değişiklikleri)
        if (user.trainerStake >= amount) {
            user.trainerStake -= amount;
        } else {
            uint256 remaining = amount - user.trainerStake;
            user.trainerStake = 0;
            user.predictorStake -= remaining;
        }

        // 3. INTERACTION (Dış Çağrı)
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "PdM:TransferFailed");

        emit StakeWithdrawn(msg.sender, amount);
    }
    
    // --- CORE LOGIC ---

    function registerModel(
        bytes32 modelCommitment, bytes32 modelType, bytes32 domainType, uint256 claimedAccuracy,
        uint[2] calldata a, uint[2][2] calldata b, uint[2] calldata c, uint[4] calldata publicInputs
    ) external whenNotPaused onlyActiveUser hasSufficientTrainerStake(msg.sender) returns (uint256 modelId) {
        require(modelCommitment != bytes32(0) && !usedCommitments[modelCommitment], "PdM:CommitmentInvalid");
        require(publicInputs[0] == uint256(modelCommitment), "PdM:CommitmentMismatch");
        
        // Ana doğrulama fonksiyonu "verifyProof" çağrılıyor.
        // Groth16Verifier 4 public signal bekliyor
        require(zkVerifier.verifyProof(a,b,c,publicInputs), "PdM:ZkVerifyFailed");
        
        modelId = modelCounter++;
        models[modelId] = ZKModel(modelCommitment, modelType, domainType, claimedAccuracy, msg.sender, block.timestamp, true);
        usedCommitments[modelCommitment] = true;
        emit ModelRegistered(modelId, modelCommitment, msg.sender);
    }
    
    function submitSensorData(bytes32 dataCommitment, bytes32 metadataHash, uint256 machineId, Role minimumViewRole) 
    external whenNotPaused onlyActiveUser returns (uint256 dataId) {
        require(users[msg.sender].role >= Role.WORKER, "PdM:WorkerRequired");
        
        dataId = dataCounter++;
        sensorData[dataId] = SensorData(dataCommitment, metadataHash, msg.sender, block.timestamp, machineId, minimumViewRole);
        hasDataAccess[msg.sender][dataId] = true;

        emit DataSubmitted(dataId, msg.sender, machineId);
    }
    
    // --- ADMIN & VIEW FUNCTIONS ---
    
    function canAccessData(address userAddr, uint256 dataId) public view returns (bool) {
        if (dataId >= dataCounter) return false;
        UserProfile storage user = users[userAddr];
        if (!user.isActive) return false;
        if (user.role == Role.ADMIN) return true;
        if (user.role >= sensorData[dataId].minimumViewRole) return true;
        return hasDataAccess[userAddr][dataId];
    }

    function setPause(bool _status) external onlyAdmin {
        isPaused = _status;
        emit SystemPaused(_status);
    }
}